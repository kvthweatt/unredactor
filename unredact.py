"""
Interactive PDF Black Box Replacer
Click on a black box to select it, then replace all boxes of that size with white boxes containing text.

Requirements:
    pip install PyMuPDF pillow
"""

import fitz  # PyMuPDF
from PIL import Image, ImageTk, ImageDraw
import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog
import io
import cv2
import numpy as np

class PDFBoxReplacer:
    def __init__(self, root):
        self.root = root
        self.root.title("PDF Black Box Replacer")
        self.root.geometry("1000x800")
        
        self.pdf_doc = None
        self.current_page = 0
        self.all_boxes = []
        self.selected_box = None
        self.zoom = 1.0  # Changed from 1.5 to 1.0
        
        self.setup_ui()
        
    def setup_ui(self):
        # Top toolbar
        toolbar = tk.Frame(self.root)
        toolbar.pack(side=tk.TOP, fill=tk.X, padx=5, pady=5)
        
        tk.Button(toolbar, text="Open PDF", command=self.open_pdf).pack(side=tk.LEFT, padx=2)
        tk.Button(toolbar, text="Save PDF", command=self.save_pdf).pack(side=tk.LEFT, padx=2)
        tk.Button(toolbar, text="Previous Page", command=self.prev_page).pack(side=tk.LEFT, padx=2)
        tk.Button(toolbar, text="Next Page", command=self.next_page).pack(side=tk.LEFT, padx=2)
        
        # Zoom controls
        tk.Button(toolbar, text="Zoom In (+)", command=self.zoom_in).pack(side=tk.LEFT, padx=2)
        tk.Button(toolbar, text="Zoom Out (-)", command=self.zoom_out).pack(side=tk.LEFT, padx=2)
        tk.Button(toolbar, text="Fit Width", command=self.zoom_fit_width).pack(side=tk.LEFT, padx=2)
        
        self.zoom_label = tk.Label(toolbar, text=f"Zoom: {int(self.zoom * 100)}%")
        self.zoom_label.pack(side=tk.LEFT, padx=10)
        
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
        
        # Bind events
        self.canvas.bind("<Button-1>", self.on_canvas_click)
        self.canvas.bind("<MouseWheel>", self.on_mousewheel)  # Windows/Mac
        self.canvas.bind("<Button-4>", self.on_mousewheel)    # Linux scroll up
        self.canvas.bind("<Button-5>", self.on_mousewheel)    # Linux scroll down
        
        # Bind keyboard shortcuts
        self.root.bind("<Control-plus>", lambda e: self.zoom_in())
        self.root.bind("<Control-equal>", lambda e: self.zoom_in())  # + without shift
        self.root.bind("<Control-minus>", lambda e: self.zoom_out())
        self.root.bind("<Control-0>", lambda e: self.zoom_fit_width())
        
        # Status bar
        self.status_label = tk.Label(self.root, text="Click 'Open PDF' to begin", 
                                     bd=1, relief=tk.SUNKEN, anchor=tk.W)
        self.status_label.pack(side=tk.BOTTOM, fill=tk.X)

    def on_mousewheel(self, event):
        """Handle mouse wheel zoom with Ctrl held"""
        if event.state & 0x0004:  # Ctrl key is held
            if event.delta > 0 or event.num == 4:  # Scroll up
                self.zoom_in()
            elif event.delta < 0 or event.num == 5:  # Scroll down
                self.zoom_out()
            return "break"  # Prevent default scrolling
    
    def zoom_in(self):
        """Increase zoom level"""
        self.zoom = min(self.zoom * 1.25, 5.0)  # Max 500%
        self.zoom_label.config(text=f"Zoom: {int(self.zoom * 100)}%")
        self.load_page()
    
    def zoom_out(self):
        """Decrease zoom level"""
        self.zoom = max(self.zoom / 1.25, 0.25)  # Min 25%
        self.zoom_label.config(text=f"Zoom: {int(self.zoom * 100)}%")
        self.load_page()
    
    def zoom_fit_width(self):
        """Fit page width to window"""
        if not self.pdf_doc:
            return
        
        page = self.pdf_doc[self.current_page]
        canvas_width = self.canvas.winfo_width()
        page_width = page.rect.width
        
        self.zoom = (canvas_width - 20) / page_width  # 20px padding
        self.zoom = max(0.25, min(self.zoom, 5.0))  # Clamp between 25% and 500%
        self.zoom_label.config(text=f"Zoom: {int(self.zoom * 100)}%")
        self.load_page()
        
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

    def save_pdf(self):
        """Save the modified PDF"""
        if not self.pdf_doc:
            messagebox.showwarning("Warning", "No PDF loaded")
            return
        
        output_path = filedialog.asksaveasfilename(
            title="Save modified PDF as",
            defaultextension=".pdf",
            filetypes=[("PDF files", "*.pdf"), ("All files", "*.*")]
        )
        
        if output_path:
            try:
                self.pdf_doc.save(output_path)
                messagebox.showinfo("Success", f"Saved to: {output_path}")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to save: {str(e)}")
    
    def load_page(self):
        if not self.pdf_doc:
            return
        
        # Store current scroll position
        x_scroll = self.canvas.xview()[0]
        y_scroll = self.canvas.yview()[0]
        
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
        
        # Restore scroll position
        self.canvas.xview_moveto(x_scroll)
        self.canvas.yview_moveto(y_scroll)
    
    def find_boxes_on_page(self, page):
        """Find all black rectangles on the page using image processing"""
        self.all_boxes = []
        
        # Render page to image
        mat = fitz.Matrix(2, 2)  # Higher resolution for better detection
        pix = page.get_pixmap(matrix=mat)
        img_data = pix.tobytes("png")
        
        # Convert to OpenCV format
        nparr = np.frombuffer(img_data, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        
        # Threshold to find black regions
        _, thresh = cv2.threshold(gray, 50, 255, cv2.THRESH_BINARY_INV)
        
        # Find contours
        contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        # Filter for rectangular regions
        for contour in contours:
            x, y, w, h = cv2.boundingRect(contour)
            
            # Filter out very small or very large boxes
            if w > 20 and h > 10 and w < pix.width * 0.8 and h < pix.height * 0.8:
                # Convert back to PDF coordinates (accounting for 2x scaling)
                pdf_x0 = x / 2
                pdf_y0 = y / 2
                pdf_x1 = (x + w) / 2
                pdf_y1 = (y + h) / 2
                
                rect = fitz.Rect(pdf_x0, pdf_y0, pdf_x1, pdf_y1)
                
                self.all_boxes.append({
                    "rect": rect,
                    "width": round(rect.width, 1),
                    "height": round(rect.height, 1),
                    "page": self.current_page
                })
        
        print(f"Found {len(self.all_boxes)} boxes using image processing")
        for i, box in enumerate(self.all_boxes):
            print(f"  Box {i}: {box['width']}x{box['height']} at ({box['rect'].x0:.1f}, {box['rect'].y0:.1f})")
                    
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
            self.status_label.config(text="No boxes found on this page")
            return
        
        # Convert canvas coordinates to PDF coordinates
        canvas_x = self.canvas.canvasx(event.x)
        canvas_y = self.canvas.canvasy(event.y)
        pdf_x = canvas_x / self.zoom
        pdf_y = canvas_y / self.zoom
        
        print(f"Click at canvas: ({event.x}, {event.y})")
        print(f"Scrolled canvas: ({canvas_x}, {canvas_y})")
        print(f"PDF coords: ({pdf_x:.1f}, {pdf_y:.1f})")
        print(f"Checking {len(self.all_boxes)} boxes:")
        
        # Find clicked box
        for i, box in enumerate(self.all_boxes):
            rect = box["rect"]
            print(f"  Box {i}: ({rect.x0:.1f}, {rect.y0:.1f}) to ({rect.x1:.1f}, {rect.y1:.1f})")
            
            # Check if click is inside this box
            if rect.x0 <= pdf_x <= rect.x1 and rect.y0 <= pdf_y <= rect.y1:
                self.selected_box = box
                print(f"  -> SELECTED!")
                self.status_label.config(
                    text=f"Selected box: {box['width']}x{box['height']} pts. "
                         f"Click 'Replace Boxes' to replace all boxes of this size."
                )
                self.draw_boxes()  # Redraw to highlight selection
                return
        
        print("  -> No box found at click location")
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
        
        # Apply replacements to the current page in memory
        self.apply_replacements(self.selected_box["width"], 
                               self.selected_box["height"], 
                               text)
        
        # Reload the page to show changes
        self.load_page()
        
        self.status_label.config(text=f"Replaced boxes on page {self.current_page + 1}. "
                                     "Navigate pages to apply to others. Use File > Save to save changes.")

    def apply_replacements(self, target_width, target_height, text, tolerance=2.0):
        """Apply replacements to current page by modifying the page image"""
        page = self.pdf_doc[self.current_page]
        
        # Get the actual page dimensions
        page_rect = page.rect
        page_width = page_rect.width
        page_height = page_rect.height
        
        # Render page to image at ACTUAL SIZE (1x, not 2x)
        mat = fitz.Matrix(1, 1)
        pix = page.get_pixmap(matrix=mat)
        
        # Convert to PIL Image
        img_data = pix.tobytes("png")
        img = Image.open(io.BytesIO(img_data))
        draw = ImageDraw.Draw(img)
        
        count = 0
        # Find matching boxes and draw white rectangles with text
        for box in self.all_boxes:
            width = box["width"]
            height = box["height"]
            
            # Check if dimensions match (within tolerance)
            if abs(width - target_width) <= tolerance and \
               abs(height - target_height) <= tolerance:
                
                rect = box["rect"]
                x0 = rect.x0
                y0 = rect.y0
                x1 = rect.x1
                y1 = rect.y1
                
                # Draw white rectangle
                draw.rectangle([x0, y0, x1, y1], fill='white', outline='black', width=1)
                
                # Add text
                font_size = int(min(height * 0.6, 12))
                try:
                    from PIL import ImageFont
                    font = ImageFont.truetype("arial.ttf", font_size)
                except:
                    font = ImageFont.load_default()
                
                # Center the text
                bbox = draw.textbbox((0, 0), text, font=font)
                text_width = bbox[2] - bbox[0]
                text_height = bbox[3] - bbox[1]
                text_x = x0 + (x1 - x0 - text_width) / 2
                text_y = y0 + (y1 - y0 - text_height) / 2
                
                draw.text((text_x, text_y), text, fill='black', font=font)
                count += 1
        
        if count > 0:
            # Save modified image
            img_bytes = io.BytesIO()
            img.save(img_bytes, format='PNG')
            img_bytes.seek(0)
            
            # Create a new blank page with exact dimensions
            temp_pdf = fitz.open()
            new_page = temp_pdf.new_page(width=page_width, height=page_height)
            
            # Insert the image to fill the entire page
            new_page.insert_image(page_rect, stream=img_bytes.read())
            
            # Replace the page in the main document
            self.pdf_doc.delete_page(self.current_page)
            self.pdf_doc.insert_pdf(temp_pdf, from_page=0, to_page=0, start_at=self.current_page)
            
            temp_pdf.close()
        
        return count
    
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
