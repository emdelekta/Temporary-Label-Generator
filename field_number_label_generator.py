import tkinter as tk
from tkinter import filedialog, messagebox
import pandas as pd
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.graphics.barcode import code128
import os


class LabelApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Field Number Label Generator")

        self.master_df = None
        self.query_df = None

        self.downloads_path = os.path.expanduser("~/Downloads")

        self.master_label = tk.Label(root, text="Master: NOT LOADED", fg="red")
        self.master_label.pack()

        tk.Button(
            root, text="1. Load MASTER Spreadsheet", command=self.load_master
        ).pack(pady=5)

        self.query_label = tk.Label(root, text="Field List: NOT LOADED", fg="red")
        self.query_label.pack()

        tk.Button(root, text="2. Load FIELD NUMBER List", command=self.load_query).pack(
            pady=5
        )

        tk.Button(
            root, text="3. Generate Label Sheet", command=self.generate_labels
        ).pack(pady=10)

    def load_master(self):
        path = filedialog.askopenfilename(
            initialdir=self.downloads_path, filetypes=[("Excel files", "*.xlsx *.xls")]
        )
        if path:
            try:
                self.master_df = pd.read_excel(path)
                self.master_label.config(text="Master: LOADED", fg="green")
            except Exception as e:
                messagebox.showerror("Error", str(e))

    def load_query(self):
        path = filedialog.askopenfilename(
            initialdir=self.downloads_path, filetypes=[("Excel files", "*.xlsx *.xls")]
        )
        if path:
            try:
                self.query_df = pd.read_excel(path)
                self.query_label.config(text="Field List: LOADED", fg="green")
            except Exception as e:
                messagebox.showerror("Error", str(e))

    def safe(self, v):
        if pd.isna(v):
            return ""
        return str(v).strip()

    def generate_labels(self):
        if self.master_df is None or self.query_df is None:
            messagebox.showwarning("Warning", "Load both spreadsheets first.")
            return

        q = self.query_df["Field Number"].astype(str).str.strip()
        m = self.master_df["Field Number"].astype(str).str.strip()

        missing = q[~q.isin(m)]
        if not missing.empty:
            messagebox.showwarning(
                "Missing Field Numbers", "Missing:\n" + "\n".join(missing.tolist())
            )

        records = self.master_df[m.isin(q)]
        if records.empty:
            messagebox.showerror("Error", "No matches found.")
            return

        file_path = filedialog.asksaveasfilename(
            initialdir=self.downloads_path,
            defaultextension=".pdf",
            filetypes=[("PDF", "*.pdf")],
        )
        if not file_path:
            return

        self.create_pdf(records, file_path)


    def create_pdf(self, records, file_path):
        doc = SimpleDocTemplate(file_path, pagesize=(8.5 * inch, 11 * inch))

        # Set font
        regular_font_path = os.path.join(
            "fonts", "WorkSans", "WorkSans-Regular.ttf"
        )
        italic_font_path = os.path.join(
            "fonts", "WorkSans", "WorkSans-Italic.ttf"
        )
        bold_font_path = os.path.join(
            "fonts", "WorkSans", "WorkSans-Bold.ttf"
        )
        bolditalic_font_path = os.path.join(
            "fonts", "WorkSans", "WorkSans-BoldItalic.ttf"
        )
        pdfmetrics.registerFont(TTFont("WorkSans-Regular", regular_font_path))
        pdfmetrics.registerFont(TTFont("WorkSans-Italic", italic_font_path))
        pdfmetrics.registerFont(TTFont("WorkSans-Bold", bold_font_path))
        pdfmetrics.registerFont(TTFont("WorkSans-BoldItalic", bolditalic_font_path))

        FONT_SIZE = 7

        field_style = ParagraphStyle(
            name="Field", fontName="WorkSans-Bold", fontSize=FONT_SIZE + 2, leading=FONT_SIZE + 2
        )

        body_style = ParagraphStyle(name="Body", fontName="WorkSans-Regular", fontSize=FONT_SIZE)

        taxon_style = ParagraphStyle(name="Taxon", fontName="WorkSans-Italic", fontSize=FONT_SIZE)

        label_w = 2.5 * inch
        label_h = 2.0 * inch
        cols = int(8.5 * inch // label_w)

        labels = []

        for _, r in records.iterrows():
            fn = self.safe(r.get("Field Number"))
            count = self.safe(r.get("Count"))

            n_text = f"n = {count}" if count else "n = __"

            barcode = code128.Code128(fn, barHeight=0.35 * inch, barWidth=0.01 * inch)

            clade = self.safe(r.get("Clade/Family"))
            genus = self.safe(r.get("Genus"))
            species = self.safe(r.get("Species"))

            gensp = " ".join([x for x in [genus, species] if x])

            lat = self.safe(r.get("End Lat"))
            lon = self.safe(r.get("End Long"))
            coord = f"({lat}, {lon})" if lat and lon else ""

            maxd = self.safe(r.get("Start (Max) Depth (m)"))
            mind = self.safe(r.get("End (Min) Depth (m)"))
            depth = ""
            if maxd or mind:
                parts = []
                if maxd:
                    parts.append(f"Max = {maxd}")
                if mind:
                    parts.append(f"Min = {mind}")
                depth = "Depth (m): " + " | ".join(parts)

            date = self.safe(r.get("Date Collected"))

            # TRUE CORNER LAYOUT TABLE
            label = Table(
                [
                    [
                        Paragraph(fn, field_style),
                        Paragraph(n_text, body_style),
                    ],
                    [barcode, ""],
                    [
                        Paragraph(clade, body_style),
                        Paragraph(gensp, taxon_style),
                    ],
                    [Paragraph(coord, body_style), ""],
                    [Paragraph(depth, body_style), ""],
                    [Paragraph(date, body_style), ""],
                ],
                colWidths=[label_w * 0.7, label_w * 0.3],
            )

            label.setStyle(
                TableStyle(
                    [
                        ("SPAN", (0, 1), (1, 1)),
                        ("SPAN", (0, 2), (1, 2)),
                        ("SPAN", (0, 3), (1, 3)),
                        ("SPAN", (0, 4), (1, 4)),
                        ("SPAN", (0, 5), (1, 5)),
                        ("GRID", (0, 0), (-1, -1), 0.25, colors.transparent),
                        ("LINESTYLE", (0, 0), (-1, -1), "dotted"),
                        ("VALIGN", (0, 0), (-1, -1), "TOP"),
                        ("ALIGN", (1, 0), (1, 0), "RIGHT"),
                        ("LEFTPADDING", (0, 0), (-1, -1), 3),
                        ("RIGHTPADDING", (0, 0), (-1, -1), 3),
                        ("TOPPADDING", (0, 0), (-1, -1), 2),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
                    ]
                )
            )

            labels.append(label)

        grid = []
        row = []

        for i, l in enumerate(labels):
            row.append(l)
            if (i + 1) % cols == 0:
                grid.append(row)
                row = []

        if row:
            while len(row) < cols:
                row.append("")
            grid.append(row)

        master = Table(grid, colWidths=[label_w] * cols)

        master.setStyle(
            TableStyle(
                [
                    ("GRID", (0, 0), (-1, -1), 0.25, colors.black),
                    ("LINESTYLE", (0, 0), (-1, -1), "dotted"),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ]
            )
        )

        doc.build([master])
        messagebox.showinfo("Done", "Labels created successfully.")


if __name__ == "__main__":
    root = tk.Tk()
    app = LabelApp(root)
    root.mainloop()
