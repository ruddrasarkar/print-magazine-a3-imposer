import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from pathlib import Path
from PIL import Image, ImageTk
from reportlab.pdfgen import canvas
from reportlab.lib.units import mm
from reportlab.lib.utils import ImageReader
import re, math

A3_W, A3_H = 420*mm, 297*mm
A4_W, A4_H = 210*mm, 297*mm

def natural_key(p):
    nums = re.findall(r'\d+', p.stem)
    return (int(nums[-1]) if nums else 10**9, p.stem.lower())

def impose_pairs(n):
    if n % 4:
        raise ValueError("Booklet page count must be divisible by 4.")
    pairs = []
    lo, hi = 1, n
    while lo < hi:
        pairs += [(hi, lo), (lo+1, hi-1)]
        lo += 2
        hi -= 2
    return pairs

class Imposer:
    def __init__(self, root):
        self.root = root
        root.title("Print Magazine BD — A3 Imposer")
        root.geometry("980x720")
        root.minsize(900, 650)
        self.files = []
        self.preview_img = None

        top = tk.Frame(root, padx=18, pady=14)
        top.pack(fill="x")
        tk.Label(top, text="PRINT MAGAZINE BD", font=("Arial", 20, "bold")).pack(anchor="w")
        tk.Label(top, text="A4 → A3 Magazine Imposer", font=("Arial", 11)).pack(anchor="w")

        controls = tk.Frame(root, padx=18, pady=8)
        controls.pack(fill="x")

        tk.Button(controls, text="📁 Choose Page Folder", command=self.choose_folder,
                  font=("Arial", 11, "bold"), padx=12, pady=7).grid(row=0,column=0,padx=5)
        tk.Button(controls, text="🖼 Preview", command=self.preview,
                  padx=12, pady=7).grid(row=0,column=1,padx=5)
        tk.Button(controls, text="📄 Export A3 PDF", command=self.export,
                  font=("Arial", 11, "bold"), padx=12, pady=7).grid(row=0,column=2,padx=5)

        tk.Label(controls, text="Bleed (mm):").grid(row=1,column=0,sticky="e",pady=12)
        self.bleed = tk.DoubleVar(value=3)
        tk.Spinbox(controls, from_=0, to=20, increment=0.5, textvariable=self.bleed, width=8).grid(row=1,column=1,sticky="w")

        self.info = tk.Label(root, text="No pages selected", anchor="w", padx=18)
        self.info.pack(fill="x")

        body = tk.Frame(root, padx=18, pady=8)
        body.pack(fill="both", expand=True)

        left = tk.Frame(body)
        left.pack(side="left", fill="y")
        tk.Label(left, text="Detected pages", font=("Arial", 12, "bold")).pack(anchor="w")
        self.listbox = tk.Listbox(left, width=32, height=24)
        self.listbox.pack(fill="y", pady=8)

        right = tk.Frame(body)
        right.pack(side="left", fill="both", expand=True, padx=(24,0))
        tk.Label(right, text="A3 Preview", font=("Arial", 12, "bold")).pack(anchor="w")
        self.preview_label = tk.Label(right, text="Choose a folder to begin",
                                      relief="groove", bg="#eeeeee")
        self.preview_label.pack(fill="both", expand=True, pady=8)

        self.status = tk.Label(root, text="Ready", anchor="w", padx=18, pady=7)
        self.status.pack(fill="x")

    def choose_folder(self):
        folder = filedialog.askdirectory(title="Select magazine page folder")
        if not folder: return
        candidates = []
        for ext in ("*.jpg","*.jpeg","*.png","*.webp"):
            candidates += list(Path(folder).glob(ext))
        candidates.sort(key=natural_key)
        if not candidates:
            messagebox.showerror("No pages", "No JPG, PNG, JPEG or WEBP pages found.")
            return
        self.files = candidates
        self.listbox.delete(0, "end")
        for i,p in enumerate(self.files, 1):
            self.listbox.insert("end", f"{i:02d}  {p.name}")
        if len(self.files) % 4:
            self.info.config(text=f"{len(self.files)} pages — add {4-len(self.files)%4} blank page(s).")
        else:
            self.info.config(text=f"{len(self.files)} pages — ready for imposition.")
        self.preview()

    def make_sheet_image(self, left_path, right_path):
        from PIL import ImageDraw, ImageFont
        W,H = 842, 594
        out = Image.new("RGB",(W,H),"white")
        draw = ImageDraw.Draw(out)
        half=W//2
        def place(path, x):
            if path:
                im=Image.open(path).convert("RGB")
                im.thumbnail((half-12,H-12), Image.Resampling.LANCZOS)
                xx=x+(half-im.width)//2
                yy=(H-im.height)//2
                out.paste(im,(xx,yy))
        place(left_path,0); place(right_path,half)
        draw.line((half,0,half,H), fill="gray", width=2)
        return out

    def preview(self):
        if not self.files: return
        n=len(self.files)
        if n%4:
            self.status.config(text="Preview unavailable until page count is divisible by 4.")
            return
        pairs=impose_pairs(n)
        a,b=pairs[0]
        img=self.make_sheet_image(self.files[a-1],self.files[b-1])
        img.thumbnail((620,620),Image.Resampling.LANCZOS)
        self.preview_img=ImageTk.PhotoImage(img)
        self.preview_label.config(image=self.preview_img, text="")
        self.status.config(text=f"Preview: sheet 1 — pages {a} | {b}")

    def export(self):
        if not self.files:
            messagebox.showwarning("No pages","Choose a page folder first.")
            return
        n=len(self.files)
        if n%4:
            messagebox.showerror("Invalid page count",
                f"{n} pages detected. Booklets require a multiple of 4.")
            return
        out=filedialog.asksaveasfilename(
            title="Export A3 print PDF",
            defaultextension=".pdf",
            filetypes=[("PDF files","*.pdf")],
            initialfile="Magazine_A3_Print_Ready.pdf")
        if not out: return

        pairs=impose_pairs(n)
        c=canvas.Canvas(out, pagesize=(A3_W,A3_H))
        bleed=float(self.bleed.get())*mm

        # Each pair becomes one A3 side. Pages are fitted to A4 landscape side-by-side.
        # Page images are drawn at their native A4 proportion inside each half.
        for idx,(lp,rp) in enumerate(pairs):
            for side,(p1,p2) in enumerate(((lp,rp), (None,None))):
                # The pair list already represents the sequential printer-side order:
                # each pair is one physical side.
                pass

        # Correct saddle-stitch sequence: every 2 pairs form front/back of one sheet.
        # pairs: outside, inside, next outside, next inside...
        for sheet in range(0,len(pairs),2):
            outside=pairs[sheet]
            inside=pairs[sheet+1]
            for p1,p2 in (outside,inside):
                for path, x in ((self.files[p1-1],0),(self.files[p2-1],A3_W/2)):
                    im=Image.open(path)
                    iw,ih=im.size
                    box_w=A3_W/2
                    box_h=A3_H
                    scale=min((box_w-2*bleed)/iw,(box_h-2*bleed)/ih)
                    dw,dh=iw*scale,ih*scale
                    x0=x+(box_w-dw)/2
                    y0=(A3_H-dh)/2
                    c.drawImage(ImageReader(im),x0,y0,width=dw,height=dh,
                                preserveAspectRatio=True,mask='auto')
                c.line(A3_W/2,0,A3_W/2,A3_H)
                c.showPage()
        c.save()
        self.status.config(text=f"Exported: {Path(out).name}")
        messagebox.showinfo("Done", f"Created:\n{out}")

if __name__=="__main__":
    root=tk.Tk()
    Imposer(root)
    root.mainloop()
