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
import logging

logging.basicConfig(level=logging.DEBUG)
applog = logging.getLogger(__name__)


class LabelApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Field Number Label Generator")

        self.master_df = None
        self.query_df = None
        self.downloads_path = os.path.expanduser("~/Downloads")

        self.cruise_year = tk.StringVar()
        self.box_number = tk.StringVar()

        self.master_label = tk.Label(root, text="Master: NOT LOADED", fg="red")
        self.master_label.pack()

        tk.Button(root, text="1. Load MASTER Spreadsheet", command=self.load_master).pack(pady=5)

        self.query_label = tk.Label(root, text="Field List: NOT LOADED", fg="red")
        self.query_label.pack()

        tk.Button(root, text="2. Load FIELD NUMBER List", command=self.load_query).pack(pady=5)

        meta_frame = tk.LabelFrame(root, text="Additional Information")
        meta_frame.pack(pady=10, padx=10, fill="x")

        tk.Label(meta_frame, text="Cruise Year:").grid(row=0, column=0, sticky="e", padx=5, pady=2)
        tk.Entry(meta_frame, textvariable=self.cruise_year, width=15).grid(row=0, column=1, sticky="w", padx=5)
        tk.Label(meta_frame, text="Box Number:").grid(row=0, column=2, sticky="e", padx=5, pady=2)
        tk.Entry(meta_frame, textvariable=self.box_number, width=15).grid(row=0, column=3, sticky="w", padx=5)   
        
        tk.Button(root, text="3. Generate Label Sheet", command=self.generate_labels).pack(pady=10)

    def load_master(self):
        path = filedialog.askopenfilename(
            initialdir=self.downloads_path,
            filetypes=[("Excel files", "*.xlsx *.xls")],
        )
        if path:
            self.master_df = pd.read_excel(path)
            self.master_df = self.master_df.astype(str).replace(r'\.0$', '', regex=True)
            self.master_label.config(text="Master: LOADED", fg="green")

    def load_query(self):
        path = filedialog.askopenfilename(
            initialdir=self.downloads_path,
            filetypes=[("Excel files", "*.xlsx *.xls")],
        )
        if path:
            self.query_df = pd.read_excel(path)
            self.query_label.config(text="Field List: LOADED", fg="green")

    def safe(self, v):
        return "" if pd.isna(v) else str(v).strip()

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
        
        cruise_year = self.cruise_year.get().strip()
        box_number = self.box_number.get().strip()
        applog.debug(f"Cruise (GUI): '{cruise_year}'")
        applog.debug(f"Box (GUI): '{box_number}'")

        file_path = filedialog.asksaveasfilename(
            initialdir=self.downloads_path,
            defaultextension=".pdf",
            filetypes=[("PDF", "*.pdf")],
        )
        if file_path:
            self.create_pdf(records, file_path, cruise_year, box_number)

    def create_pdf(self, records, file_path, cruise_year, box_number):
        doc = SimpleDocTemplate(file_path, pagesize=(8.5 * inch, 11 * inch))

        # ---------- FONT SETUP (matches your folder screenshot) ----------
        script_dir = os.path.dirname(os.path.abspath(__file__))
        fonts_dir = os.path.join(script_dir, "fonts", "WorkSans")

        pdfmetrics.registerFont(TTFont("WorkSans-Regular", os.path.join(fonts_dir, "WorkSans-Regular.ttf")))
        pdfmetrics.registerFont(TTFont("WorkSans-Italic", os.path.join(fonts_dir, "WorkSans-Italic.ttf")))
        pdfmetrics.registerFont(TTFont("WorkSans-Bold", os.path.join(fonts_dir, "WorkSans-Bold.ttf")))
        # ---------------------------------------------------------------

        FONT_SIZE = 7

        field_style = ParagraphStyle(
            name="Field",
            fontName="WorkSans-Bold",
            fontSize=FONT_SIZE + 4,
            leading=FONT_SIZE + 2,
            alignment=1,  # Center
        )

        body_style = ParagraphStyle(
            name="Body",
            fontName="WorkSans-Regular",
            fontSize=FONT_SIZE,
            leading=FONT_SIZE,
            spaceBefore=0,
            spaceAfter=0,
        )

        taxon_style = ParagraphStyle(
            name="Taxon",
            fontName="WorkSans-Italic",
            fontSize=FONT_SIZE,
            leading=FONT_SIZE,
            spaceBefore=0,
            spaceAfter=0,
        )

        additional_label_style = ParagraphStyle(
            name="AdditionalLabel",
            fontName="WorkSans-Regular",
            fontSize=FONT_SIZE,
            leading=FONT_SIZE,
            alignment=1,  # Center
        )

        additional_value_style = ParagraphStyle(
            name="AdditionalValue",
            fontName="WorkSans-Regular",
            fontSize=FONT_SIZE,
            leading=FONT_SIZE,
            alignment=1,  # Center
        )

        label_w = 2.5 * inch
        label_h = 2.0 * inch
        cols = int(8.5 * inch // label_w)

        labels = []

        for _, r in records.iterrows():
            fn = self.safe(r.get("Field Number"))
            count = self.safe(r.get("Count"))
            n_text = f'<font name="WorkSans-Italic">n</font> = {count}' if count else f'<font name="WorkSans-Italic">n</font> = __'

            barcode = code128.Code128(fn, barHeight=0.35 * inch, barWidth=0.01 * inch)

            clade = self.safe(r.get("Clade/Family"))
            applog.debug(f"Clade/Family: '{clade}'")
            genus = self.safe(r.get("Genus"))
            applog.debug(f"Genus: '{genus}'")
            species = self.safe(r.get("species"))
            applog.debug(f"Species: '{species}'")
            gensp = " ".join(x for x in [genus, species] if x)
            applog.debug(f"Genus/Species: '{gensp}'")

            taxon_parts = []
            
            if clade:
                taxon_parts.append(clade)

            if gensp:
                taxon_parts.append(
                    f'<font name="WorkSans-Italic">{gensp}</font>'
                )

            taxon_para = Paragraph(" ".join(taxon_parts), body_style)


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

            cruise_block = Paragraph(f"<u>Cruise</u><br/>{cruise_year}", additional_label_style,)
            applog.debug(f"Cruise: '{cruise_year}'")
            box_block = Paragraph(f"<u>Box</u><br/>{box_number}", additional_label_style,)
            applog.debug(f"Box: '{box_number}'")

            additional_table = Table(
                [
                    [cruise_block],
                    [box_block],
                ],
                colWidths=[label_w * 0.3],
                rowHeights=[None, None],
            )

            additional_table.setStyle(
                TableStyle(
                    [            
                        ("TOPPADDING", (0, 0), (-1, -1), 0),  
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 0),           
                        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                        ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ]
                )
            )

            label = Table(
                [
                    [Paragraph(fn, field_style), Paragraph(n_text, body_style)],
                    [barcode, additional_table],
                    [taxon_para, ""],
                    [Paragraph(coord, body_style), ""],
                    [Paragraph(depth, body_style), ""],
                    [Paragraph(date, body_style), ""],
                ],
                colWidths=[label_w * 0.7, label_w * 0.3],
                rowHeights=[
                    0.28 * inch,  # Field number and n
                    0.42 * inch, # Barcode and additional info
                    None, None, None, None
                ]
            )

            label.setStyle(
                TableStyle(
                    [
                        ("BOX", (0, 0), (-1, -1), 0.5, colors.black, 1, (1, 2)),
                        # ("SPAN", (0, 1), (1, 1)),
                        ("SPAN", (0, 2), (1, 2)),
                        ("SPAN", (0, 3), (1, 3)),
                        ("SPAN", (0, 4), (1, 4)),
                        ("SPAN", (0, 5), (1, 5)),
                        ("VALIGN", (0, 0), (-1, -1), "TOP"),
                        ("ALIGN", (1, 0), (1, 0), "RIGHT"),
                        ("ALIGN", (1, 1), (1, 1), "CENTER"),
                        ("VALIGN", (1, 1), (1, 1), "TOP"),
                        ("LEFTPADDING", (0, 0), (-1, -1), 3),
                        ("RIGHTPADDING", (0, 0), (-1, -1), 3),
                        ("TOPPADDING", (0, 0), (-1, -1), 0.5),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 0.5),
                    ]
                )
            )

            labels.append(label)

        grid, row = [], []
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
        doc.build([master])
        messagebox.showinfo("Done", "Labels created successfully.")


if __name__ == "__main__":
    root = tk.Tk()
    app = LabelApp(root)
    root.mainloop()