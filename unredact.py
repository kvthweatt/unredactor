"""
Interactive PDF Black Box Replacer
Click on a black box to select it, then replace all boxes of that size with white boxes containing text.

Requirements:
    pip install PyMuPDF pillow
"""

import fitz  # PyMuPDF
from PIL import Image, ImageTk
import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog
import io

class PDFBoxReplacer:
    def __init__(self, root):
        self.root = root
        self.root.title("PDF Black Box Replacer")
        self.root.geometry("1000x800")
        
        self.pdf_doc = None
        self.current_page = 0
        self.all_boxes = []
        self.selected_box = None
        self.zoom = 1.5
        
        self.setup_ui()
        
    def setup_ui(self):
        # Top toolbar
        toolbar = tk.Frame(self.root)
        toolbar.pack(side=tk.TOP, fill=tk.X, padx=5, pady=5)
        
        tk.Button(toolbar, text="Open PDF", command=self.open_pdf).pack(side=tk.LEFT, padx=2)
        tk.Button(toolbar, text="Previous Page", command=self.prev_page).pack(side=tk.LEFT, padx=2)
        tk.Button(toolbar, text="Next Page", command=self.next_page).pack(side=tk.LEFT, padx=2)
        
        self.page_label = tk.Label(toolbar, text="No PDF loaded")
        self.page_label.pack(side=tk.LEFT, padx=10)
        
        tk.Button(toolbar, text="Replace Boxes", command=self.replace_boxes, 
                 bg="green", fg="white").pack(side=tk.RIGHT, padx=2)
        
        # Canvas for PDF display
        canvas_frame = tk.Frame(self.root)
        canvas_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        self.canvas = tk.Canvas(canvas_frame, bg="gray")
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # Scrollbars
        v_scroll = tk.Scrollbar(canvas_frame, orient=tk.VERTICAL, command=self.canvas.yview)
        v_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.canvas.configure(yscrollcommand=v_scroll.set)
        
        h_scroll = tk.Scrollbar(self.root, orient=tk.HORIZONTAL, command=self.canvas.xview)
        h_scroll.pack(side=tk.BOTTOM, fill=tk.X, padx=5)
        self.canvas.configure(xscrollcommand=h_scroll.set)
        
        # Bind click event
        self.canvas.bind("<Button-1>", self.on_canvas_click)
        
        # Status bar
        self.status_label = tk.Label(self.root, text="Click 'Open PDF' to begin", 
                                     bd=1, relief=tk.SUNKEN, anchor=tk.W)
        self.status_label.pack(side=tk.BOTTOM, fill=tk.X)
        
    def open_pdf(self):
        filepath = filedialog.askopenfilename(
            title="Select PDF file",
            filetypes=[("PDF files", "*.pdf"), ("All files", "*.*")]
        )
        
        if filepath:
            try:
                self.pdf_doc = fitz.open(filepath)
                self.current_page = 0
                self.selected_box = None
                self.status_label.config(text=f"Loaded: {filepath}")
                self.load_page()
            except Exception as e:
                messagebox.showerror("Error", f"Failed to open PDF: {str(e)}")
    
    def load_page(self):
        if not self.pdf_doc:
            return
        
        page = self.pdf_doc[self.current_page]
        self.page_label.config(text=f"Page {self.current_page + 1} of {len(self.pdf_doc)}")
        
        # Find all boxes on current page
        self.find_boxes_on_page(page)
        
        # Render page
        mat = fitz.Matrix(self.zoom, self.zoom)
        pix = page.get_pixmap(matrix=mat)
        img_data = pix.tobytes("png")
        
        img = Image.open(io.BytesIO(img_data))
        self.photo = ImageTk.PhotoImage(img)
        
        # Clear canvas and display image
        self.canvas.delete("all")
        self.canvas.create_image(0, 0, anchor=tk.NW, image=self.photo)
        
        # Draw boxes on canvas
        self.draw_boxes()
        
        # Update scroll region
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))
    
    def find_boxes_on_page(self, page):
        """Find all filled rectangles (potential black boxes) on the page"""
        self.all_boxes = []
        drawings = page.get_drawings()
        
        for drawing in drawings:
            if drawing["type"] == "f":  # filled path
                rect = drawing["rect"]
                # Check if it's roughly rectangular and dark colored
                if rect.width > 5 and rect.height > 5:
                    # Get fill color if available
                    fill_color = drawing.get("fill", [0, 0, 0])
                    # Consider it a "black box" if it's dark (all components < 0.3)
                    if all(c < 0.3 for c in fill_color):
                        self.all_boxes.append({
                            "rect": rect,
                            "width": round(rect.width, 1),
                            "height": round(rect.height, 1),
                            "page": self.current_page
                        })
    
    def draw_boxes(self):
        """Draw rectangles on canvas to show detected boxes"""
        for i, box in enumerate(self.all_boxes):
            rect = box["rect"]
            x0, y0 = rect.x0 * self.zoom, rect.y0 * self.zoom
            x1, y1 = rect.x1 * self.zoom, rect.y1 * self.zoom
            
            # Highlight selected box
            if self.selected_box and \
               box["width"] == self.selected_box["width"] and \
               box["height"] == self.selected_box["height"]:
                color = "red"
                width = 3
            else:
                color = "blue"
                width = 2
            
            tag = f"box_{i}"
            self.canvas.create_rectangle(x0, y0, x1, y1, 
                                        outline=color, width=width, tags=tag)
    
    def on_canvas_click(self, event):
        """Handle click on canvas to select a box"""
        if not self.all_boxes:
            return
        
        # Convert canvas coordinates to PDF coordinates
        canvas_x = self.canvas.canvasx(event.x)
        canvas_y = self.canvas.canvasy(event.y)
        pdf_x = canvas_x / self.zoom
        pdf_y = canvas_y / self.zoom
        
        # Find clicked box
        for box in self.all_boxes:
            rect = box["rect"]
            if rect.x0 <= pdf_x <= rect.x1 and rect.y0 <= pdf_y <= rect.y1:
                self.selected_box = box
                self.status_label.config(
                    text=f"Selected box: {box['width']}x{box['height']} pts. "
                         f"Click 'Replace Boxes' to replace all boxes of this size."
                )
                self.draw_boxes()  # Redraw to highlight selection
                return
        
        self.status_label.config(text="No box found at click location")
    
    def prev_page(self):
        if self.pdf_doc and self.current_page > 0:
            self.current_page -= 1
            self.load_page()
    
    def next_page(self):
        if self.pdf_doc and self.current_page < len(self.pdf_doc) - 1:
            self.current_page += 1
            self.load_page()
    
    def replace_boxes(self):
        """Replace all boxes matching the selected box dimensions"""
        if not self.pdf_doc:
            messagebox.showwarning("Warning", "No PDF loaded")
            return
        
        if not self.selected_box:
            messagebox.showwarning("Warning", "No box selected. Click on a box first.")
            return
        
        # Ask for replacement text
        text = simpledialog.askstring("Replacement Text", 
                                     "Enter text to place in white boxes:")
        if not text:
            return
        
        # Ask for output filename
        output_path = filedialog.asksaveasfilename(
            title="Save modified PDF as",
            defaultextension=".pdf",
            filetypes=[("PDF files", "*.pdf"), ("All files", "*.*")]
        )
        
        if not output_path:
            return
        
        try:
            count = self.replace_all_matching_boxes(
                self.selected_box["width"],
                self.selected_box["height"],
                text,
                output_path
            )
            messagebox.showinfo("Success", 
                              f"Replaced {count} boxes.\nSaved to: {output_path}")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to replace boxes: {str(e)}")
    
    def replace_all_matching_boxes(self, target_width, target_height, text, output_path, tolerance=2.0):
        """Replace all boxes of matching size across all pages"""
        count = 0
        
        for page_num in range(len(self.pdf_doc)):
            page = self.pdf_doc[page_num]
            drawings = page.get_drawings()
            
            for drawing in drawings:
                if drawing["type"] == "f":
                    rect = drawing["rect"]
                    width = round(rect.width, 1)
                    height = round(rect.height, 1)
                    
                    # Check if dimensions match (within tolerance)
                    if abs(width - target_width) <= tolerance and \
                       abs(height - target_height) <= tolerance:
                        
                        # Check if it's a dark box
                        fill_color = drawing.get("fill", [0, 0, 0])
                        if all(c < 0.3 for c in fill_color):
                            # Draw white rectangle
                            page.draw_rect(rect, color=(1, 1, 1), fill=(1, 1, 1))
                            
                            # Add text
                            font_size = min(rect.height * 0.6, 12)
                            page.insert_textbox(rect, text, 
                                              fontsize=font_size,
                                              color=(0, 0, 0),
                                              align=fitz.TEXT_ALIGN_CENTER)
                            count += 1
        
        # Save modified PDF
        self.pdf_doc.save(output_path)
        return count

def main():
    root = tk.Tk()
    app = PDFBoxReplacer(root)
    root.mainloop()

if __name__ == "__main__":
    main()