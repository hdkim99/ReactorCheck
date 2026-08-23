"""Tk desktop GUI; every action delegates to the application service layer."""

from __future__ import annotations

import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk
from typing import Any, cast

from reactorcheck.gui_controller import GUIController
from reactorcheck.io import (
    load_config,
    save_config,
    suggest_mappings,
)
from reactorcheck.models import (
    AnalysisConfig,
    ChannelMapping,
    Species,
    SteadyStateSettings,
)


class ReactorCheckApp(ttk.Frame):
    """Mapping, analysis, QC inspection, and export workflow."""

    def __init__(self, master: tk.Misc, controller: GUIController | None = None) -> None:
        super().__init__(master, padding=10)
        self.controller = controller or GUIController()
        self.mappings: list[dict[str, str]] = []
        self._variables()
        self._build()
        self.pack(fill="both", expand=True)

    def _variables(self) -> None:
        self.data_path = tk.StringVar()
        self.time_column = tk.StringVar()
        self.time_unit = tk.StringVar(value="min")
        self.reference = tk.StringVar()
        self.catalyst_mass = tk.StringVar(value="0.5 g")
        self.steady_variables = tk.StringVar()
        self.minimum_window = tk.StringVar(value="5")
        self.slope_tolerance = tk.StringVar(value="0.02")
        self.variation_tolerance = tk.StringVar(value="0.02")
        self.manual_start = tk.StringVar()
        self.manual_end = tk.StringVar()
        self.standard_temperature = tk.StringVar(value="273.15 K")
        self.standard_pressure = tk.StringVar(value="1 atm")
        self.reactor_volume = tk.StringVar()
        self.volumetric_feed = tk.StringVar()
        self.mass_feed = tk.StringVar()
        self.sty_product = tk.StringVar()
        self.map_column = tk.StringVar()
        self.map_species = tk.StringVar()
        self.map_formula = tk.StringVar()
        self.map_role = tk.StringVar(value="product")
        self.map_unit = tk.StringVar(value="mol/h")
        self.map_inlet = tk.StringVar()
        self.map_inlet_column = tk.StringVar()
        self.map_inlet_unit = tk.StringVar(value="mol/h")
        self.status = tk.StringVar(value="Load CSV/XLSX data to begin.")

    def _build(self) -> None:
        notebook = ttk.Notebook(self)
        setup = ttk.Frame(notebook, padding=8)
        results = ttk.Frame(notebook, padding=8)
        notebook.add(setup, text="Setup & mapping")
        notebook.add(results, text="Results & QC")
        notebook.pack(fill="both", expand=True)

        file_row = ttk.Frame(setup)
        file_row.pack(fill="x")
        ttk.Entry(file_row, textvariable=self.data_path).pack(side="left", fill="x", expand=True)
        ttk.Button(file_row, text="Load data", command=self.load_data).pack(side="left", padx=4)
        ttk.Button(file_row, text="Load config", command=self.load_config_file).pack(
            side="left", padx=4
        )

        base = ttk.LabelFrame(setup, text="Experiment", padding=6)
        base.pack(fill="x", pady=6)
        self.time_box = cast(
            ttk.Combobox,
            self._field(base, "Time column", self.time_column, 0, combo=True),
        )
        self._field(base, "Time unit", self.time_unit, 0, column=2)
        self.reference_box = cast(
            ttk.Combobox,
            self._field(base, "Reference reactant", self.reference, 1, combo=True),
        )
        self._field(base, "Catalyst mass", self.catalyst_mass, 1, column=2)
        self._field(base, "Standard T", self.standard_temperature, 2)
        self._field(base, "Standard P", self.standard_pressure, 2, column=2)
        self._field(base, "Reactor volume", self.reactor_volume, 3)
        self._field(base, "Volumetric feed", self.volumetric_feed, 3, column=2)
        self._field(base, "Mass feed", self.mass_feed, 4)
        self.sty_box = cast(
            ttk.Combobox,
            self._field(base, "STY product", self.sty_product, 4, column=2, combo=True),
        )

        mapping = ttk.LabelFrame(setup, text="Species column mapping", padding=6)
        mapping.pack(fill="both", expand=True)
        editor = ttk.Frame(mapping)
        editor.pack(fill="x")
        self.map_column_box = cast(
            ttk.Combobox,
            self._field(editor, "Column", self.map_column, 0, combo=True),
        )
        self._field(editor, "Species", self.map_species, 0, column=2)
        self._field(editor, "Formula", self.map_formula, 1)
        role = cast(
            ttk.Combobox,
            self._field(editor, "Role", self.map_role, 1, column=2, combo=True),
        )
        role.configure(values=("reactant", "product", "inert"), state="readonly")
        self._field(editor, "Outlet unit", self.map_unit, 2)
        self._field(editor, "Constant inlet", self.map_inlet, 2, column=2)
        self.map_inlet_column_box = cast(
            ttk.Combobox,
            self._field(editor, "Inlet column", self.map_inlet_column, 3, combo=True),
        )
        self._field(editor, "Inlet column unit", self.map_inlet_unit, 3, column=2)
        ttk.Button(editor, text="Add/update mapping", command=self.upsert_mapping).grid(
            row=4, column=0, pady=4
        )
        ttk.Button(editor, text="Remove selected", command=self.remove_mapping).grid(
            row=4, column=2, pady=4
        )
        self.mapping_tree = ttk.Treeview(
            mapping,
            columns=(
                "column",
                "species",
                "formula",
                "role",
                "unit",
                "inlet",
                "inlet_column",
                "inlet_unit",
            ),
            show="headings",
            height=6,
        )
        for name in self.mapping_tree["columns"]:
            self.mapping_tree.heading(name, text=name)
            self.mapping_tree.column(name, width=105)
        self.mapping_tree.pack(fill="both", expand=True)
        self.mapping_tree.bind("<<TreeviewSelect>>", self._select_mapping)

        steady = ttk.LabelFrame(setup, text="Steady state", padding=6)
        steady.pack(fill="x", pady=6)
        self._field(steady, "Variables (comma)", self.steady_variables, 0)
        self._field(steady, "Minimum window", self.minimum_window, 0, column=2)
        self._field(steady, "Slope tolerance", self.slope_tolerance, 1)
        self._field(steady, "Variation tolerance", self.variation_tolerance, 1, column=2)
        self._field(steady, "Manual start", self.manual_start, 2)
        self._field(steady, "Manual end", self.manual_end, 2, column=2)

        actions = ttk.Frame(setup)
        actions.pack(fill="x")
        ttk.Button(actions, text="Analyze", command=self.analyze).pack(side="left")
        ttk.Button(actions, text="Save config", command=self.save_config_file).pack(
            side="left", padx=4
        )
        ttk.Label(actions, textvariable=self.status).pack(side="left", padx=10)

        self.summary_tree = ttk.Treeview(
            results, columns=("metric", "value", "unit", "n", "scope"), show="headings", height=12
        )
        for name in self.summary_tree["columns"]:
            self.summary_tree.heading(name, text=name)
            self.summary_tree.column(name, width=150)
        self.summary_tree.pack(fill="both", expand=True)
        self.qc_text = tk.Text(results, height=10, wrap="word")
        self.qc_text.pack(fill="both", expand=True, pady=6)
        export_actions = ttk.Frame(results)
        export_actions.pack(fill="x")
        ttk.Button(export_actions, text="Export Excel", command=self.export).pack(side="left")
        ttk.Button(export_actions, text="Save plot", command=self.export_plot).pack(
            side="left", padx=4
        )

    @staticmethod
    def _field(
        parent: tk.Misc,
        label: str,
        variable: tk.StringVar,
        row: int,
        column: int = 0,
        *,
        combo: bool = False,
    ) -> ttk.Entry | ttk.Combobox:
        ttk.Label(parent, text=label).grid(row=row, column=column, sticky="w", padx=3, pady=2)
        if combo:
            widget: ttk.Entry | ttk.Combobox = ttk.Combobox(parent, textvariable=variable)
        else:
            widget = ttk.Entry(parent, textvariable=variable)
        widget.grid(row=row, column=column + 1, sticky="ew", padx=3, pady=2)
        parent.columnconfigure(column + 1, weight=1)
        return widget

    def load_data(self) -> None:
        path = self.data_path.get() or filedialog.askopenfilename(
            filetypes=[("Tabular data", "*.csv *.xlsx")]
        )
        if not path:
            return
        try:
            frame = self.controller.load(path)
            self.data_path.set(path)
            columns = tuple(map(str, frame.columns))
            self.time_box.configure(values=columns)
            self.map_column_box.configure(values=columns)
            self.map_inlet_column_box.configure(values=("", *columns))
            if not self.time_column.get():
                likely_time = next((name for name in columns if "time" in name.lower()), columns[0])
                self.time_column.set(likely_time)
            self.mappings = [
                {
                    **item,
                    "role": "product",
                    "unit": "mol/h",
                    "inlet": "",
                    "inlet_column": "",
                    "inlet_unit": "mol/h",
                }
                for item in suggest_mappings(frame)
            ]
            self._refresh_mappings()
            self.status.set(f"Loaded {len(frame)} rows. Review every suggested mapping.")
        except (OSError, ValueError) as exc:
            messagebox.showerror("Load failed", str(exc))

    def upsert_mapping(self) -> None:
        item = {
            "column": self.map_column.get().strip(),
            "species": self.map_species.get().strip(),
            "formula": self.map_formula.get().strip(),
            "role": self.map_role.get().strip(),
            "unit": self.map_unit.get().strip(),
            "inlet": self.map_inlet.get().strip(),
            "inlet_column": self.map_inlet_column.get().strip(),
            "inlet_unit": self.map_inlet_unit.get().strip(),
        }
        if not all(item[key] for key in ("column", "species", "formula", "role", "unit")):
            messagebox.showerror(
                "Incomplete mapping", "Column, species, formula, role, and unit are required."
            )
            return
        self.mappings = [old for old in self.mappings if old["species"] != item["species"]]
        self.mappings.append(item)
        self._refresh_mappings()

    def remove_mapping(self) -> None:
        selected = self.mapping_tree.selection()
        if selected:
            species = str(self.mapping_tree.item(selected[0], "values")[1])
            self.mappings = [item for item in self.mappings if item["species"] != species]
            self._refresh_mappings()

    def _select_mapping(self, _event: tk.Event[Any]) -> None:
        selected = self.mapping_tree.selection()
        if not selected:
            return
        values = self.mapping_tree.item(selected[0], "values")
        variables = (
            self.map_column,
            self.map_species,
            self.map_formula,
            self.map_role,
            self.map_unit,
            self.map_inlet,
            self.map_inlet_column,
            self.map_inlet_unit,
        )
        for variable, value in zip(variables, values, strict=True):
            variable.set(value)

    def _refresh_mappings(self) -> None:
        self.mapping_tree.delete(*self.mapping_tree.get_children())
        for item in self.mappings:
            self.mapping_tree.insert(
                "",
                "end",
                values=tuple(
                    item[key]
                    for key in (
                        "column",
                        "species",
                        "formula",
                        "role",
                        "unit",
                        "inlet",
                        "inlet_column",
                        "inlet_unit",
                    )
                ),
            )
        reactants = [item["species"] for item in self.mappings if item["role"] == "reactant"]
        products = [item["species"] for item in self.mappings if item["role"] == "product"]
        self.reference_box.configure(values=reactants)
        self.sty_box.configure(values=("", *products))
        if len(reactants) == 1:
            self.reference.set(reactants[0])

    @staticmethod
    def _optional(text: str) -> str | None:
        value = text.strip()
        return value or None

    def build_config(self) -> AnalysisConfig:
        """Translate visible controls into the validated public data model."""
        channels = tuple(
            ChannelMapping(
                column=item["column"],
                species=Species(item["species"], item["formula"]),
                role=item["role"],  # type: ignore[arg-type]
                unit=item["unit"],
                inlet=self._optional(item["inlet"]),
                inlet_column=self._optional(item["inlet_column"]),
                inlet_unit=(
                    self._optional(item["inlet_unit"])
                    if self._optional(item["inlet_column"])
                    else None
                ),
            )
            for item in self.mappings
        )
        manual_start = self._optional(self.manual_start.get())
        manual_end = self._optional(self.manual_end.get())
        steady = SteadyStateSettings(
            variables=tuple(
                value.strip() for value in self.steady_variables.get().split(",") if value.strip()
            ),
            minimum_window=int(self.minimum_window.get()),
            slope_tolerance=float(self.slope_tolerance.get()),
            variation_tolerance=float(self.variation_tolerance.get()),
            manual_start=float(manual_start) if manual_start else None,
            manual_end=float(manual_end) if manual_end else None,
        )
        return AnalysisConfig(
            time_column=self.time_column.get().strip(),
            time_unit=self.time_unit.get().strip(),
            channels=channels,
            reference_reactant=self.reference.get().strip(),
            catalyst_mass=self.catalyst_mass.get().strip(),
            standard_temperature=self.standard_temperature.get().strip(),
            standard_pressure=self.standard_pressure.get().strip(),
            reactor_volume=self._optional(self.reactor_volume.get()),
            volumetric_feed=self._optional(self.volumetric_feed.get()),
            mass_feed=self._optional(self.mass_feed.get()),
            sty_product=self._optional(self.sty_product.get()),
            steady_state=steady,
        )

    def _apply_config(self, config: AnalysisConfig) -> None:
        self.time_column.set(config.time_column)
        self.time_unit.set(config.time_unit)
        self.reference.set(config.reference_reactant)
        self.catalyst_mass.set(config.catalyst_mass)
        self.standard_temperature.set(config.standard_temperature)
        self.standard_pressure.set(config.standard_pressure)
        self.reactor_volume.set(config.reactor_volume or "")
        self.volumetric_feed.set(config.volumetric_feed or "")
        self.mass_feed.set(config.mass_feed or "")
        self.sty_product.set(config.sty_product or "")
        steady = config.steady_state
        self.steady_variables.set(", ".join(steady.variables))
        self.minimum_window.set(str(steady.minimum_window))
        self.slope_tolerance.set(str(steady.slope_tolerance))
        self.variation_tolerance.set(str(steady.variation_tolerance))
        self.manual_start.set("" if steady.manual_start is None else str(steady.manual_start))
        self.manual_end.set("" if steady.manual_end is None else str(steady.manual_end))
        self.mappings = [
            {
                "column": channel.column,
                "species": channel.species.name,
                "formula": channel.species.formula,
                "role": channel.role,
                "unit": channel.unit,
                "inlet": channel.inlet or "",
                "inlet_column": channel.inlet_column or "",
                "inlet_unit": channel.inlet_unit or "mol/h",
            }
            for channel in config.channels
        ]
        self._refresh_mappings()
        self.reference.set(config.reference_reactant)

    def load_config_file(self) -> None:
        path = filedialog.askopenfilename(filetypes=[("JSON config", "*.json")])
        if path:
            try:
                self._apply_config(load_config(path))
                self.status.set(f"Loaded configuration: {Path(path).name}")
            except (OSError, ValueError) as exc:
                messagebox.showerror("Configuration failed", str(exc))

    def save_config_file(self) -> None:
        path = filedialog.asksaveasfilename(
            defaultextension=".json", filetypes=[("JSON config", "*.json")]
        )
        if path:
            try:
                save_config(self.build_config(), path)
                self.status.set(f"Saved configuration: {Path(path).name}")
            except (OSError, ValueError) as exc:
                messagebox.showerror("Configuration failed", str(exc))

    def analyze(self) -> None:
        try:
            result = self.controller.analyze(self.build_config())
            self.summary_tree.delete(*self.summary_tree.get_children())
            for row in result.summary.itertuples(index=False, name=None):
                self.summary_tree.insert("", "end", values=row)
            self.qc_text.delete("1.0", "end")
            if result.qc_issues:
                for issue in result.qc_issues:
                    self.qc_text.insert(
                        "end",
                        f"[{issue.severity}] {issue.code}: {issue.message}; rows={issue.rows}\n",
                    )
            else:
                self.qc_text.insert("end", "No QC issues detected.\n")
            self.status.set(
                "Analysis complete: "
                f"{len(result.processed)} rows, {len(result.qc_issues)} QC issues"
            )
        except (OSError, ValueError) as exc:
            messagebox.showerror("Analysis failed", str(exc))

    def export(self) -> None:
        path = filedialog.asksaveasfilename(
            defaultextension=".xlsx", filetypes=[("Excel workbook", "*.xlsx")]
        )
        if path:
            try:
                self.controller.export(path)
                self.status.set(f"Exported: {Path(path).name}")
            except (OSError, ValueError) as exc:
                messagebox.showerror("Export failed", str(exc))

    def export_plot(self) -> None:
        path = filedialog.asksaveasfilename(
            defaultextension=".png", filetypes=[("PNG figure", "*.png")]
        )
        if path:
            try:
                self.controller.save_plot(path)
                self.status.set(f"Saved plot: {Path(path).name}")
            except (OSError, ValueError) as exc:
                messagebox.showerror("Plot failed", str(exc))


def main() -> None:
    """Launch the desktop application."""
    root = tk.Tk()
    root.title("ReactorCheck 0.1.0")
    root.geometry("1100x850")
    ReactorCheckApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
