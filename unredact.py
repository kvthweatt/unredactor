"""
Written by Karac V. Thweatt
UnRedactor
Click on a black box to select it, then replace all boxes of that size with white boxes containing text.

Requirements:
    pip install PyMuPDF pillow pdfplumber

Some code borrowed from Lee Drake https://github.com/leedrake5/unredact
"""

import fitz  # PyMuPDF
from PIL import Image, ImageTk, ImageDraw
import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog, ttk
import io
import cv2
import numpy as np
import os
import glob
import html
import pdfplumber
from pathlib import Path
from datetime import datetime

class PDFBoxReplacer:
    def __init__(self, root):
        self.root = root
        self.root.title("PDF Un-Redactor")
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

        tk.Button(toolbar, text="Side-by-Side Export", command=self.export_side_by_side, 
                 bg="purple", fg="white").pack(side=tk.RIGHT, padx=2)
        tk.Button(toolbar, text="White Overlay Export", command=self.export_overlay_white, 
                 bg="orange", fg="white").pack(side=tk.RIGHT, padx=2)
        
        tk.Button(toolbar, text="Replace Boxes", command=self.replace_boxes, 
                 bg="green", fg="white").pack(side=tk.RIGHT, padx=2)
        tk.Button(toolbar, text="Unredact All", command=self.unredact_all, 
                 bg="red", fg="white").pack(side=tk.RIGHT, padx=2)
        tk.Button(toolbar, text="Auto Unredact", command=self.auto_unredact, 
                 bg="blue", fg="white").pack(side=tk.RIGHT, padx=2)
        
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

    def auto_unredact(self):
        from tkinter import filedialog, messagebox
        import os, re, tkinter as tk
        from tkinter import ttk

        pdf_dir = filedialog.askdirectory(title="Select PDF Folder")
        if not pdf_dir:
            return

        output_dir = filedialog.askdirectory(title="Select Output Folder")
        if not output_dir:
            return

        os.makedirs(output_dir, exist_ok=True)

        pdf_files = []
        for root, dirs, files in os.walk(pdf_dir):
            for file in files:
                if file.lower().endswith(".pdf"):
                    pdf_files.append(os.path.join(root, file))

        if not pdf_files:
            messagebox.showerror("Error", "No PDF files found")
            return

        pdf_files.sort()

        # Check if all files start with EFTA
        efta_mode = False
        if pdf_files:
            # Get just the filenames without paths
            filenames = [os.path.basename(f) for f in pdf_files]
            # Check if ALL start with EFTA (case-insensitive)
            efta_mode = all(fname.upper().startswith('EFTA') for fname in filenames)

        # Then when creating the progress window:
        if efta_mode:
            window_title = "Processing pedo-files..."
            status_text = "Processing pedo-files..."
        else:
            window_title = "Processing PDFs"
            status_text = "Starting…"

        progress_window = tk.Toplevel()
        progress_window.title(window_title)

        progress_var = tk.IntVar(value=0)
        progress_bar = ttk.Progressbar(
            progress_window,
            maximum=len(pdf_files),
            variable=progress_var
        )
        progress_bar.pack(fill="x", padx=10, pady=10)

        status_label = ttk.Label(progress_window, text=status_text)
        status_label.pack(pady=5)

        progress_window.update()

        html_files = []
        processed_count = 0
        error_count = 0

        # PASS 1 — Generate HTML
        for i, pdf_path in enumerate(pdf_files):
            try:
                if efta_mode:
                    status_label.config(text=f"Processing pedo-file: {os.path.basename(pdf_path)}")
                else:
                    status_label.config(text=f"Processing: {os.path.basename(pdf_path)}")
                progress_window.update()

                text_by_page, ocr_mode = self.extract_text_from_pdf(pdf_path)
                if not text_by_page:
                    error_count += 1
                    continue

                # FIX: Get actual previous and next files
                prev_file = None
                next_file = None
                
                if i > 0:
                    prev_pdf = pdf_files[i - 1]
                    prev_file = os.path.splitext(os.path.basename(prev_pdf))[0] + ".html"
                
                if i < len(pdf_files) - 1:
                    next_pdf = pdf_files[i + 1]
                    next_file = os.path.splitext(os.path.basename(next_pdf))[0] + ".html"

                html_path = self.create_html_from_text(
                    pdf_path,
                    text_by_page,
                    ocr_mode,
                    output_dir,
                    prev_file=prev_file,  # Pass the actual previous file
                    next_file=next_file   # Pass the actual next file
                )

                html_files.append(os.path.basename(html_path))
                processed_count += 1

                progress_var.set(i + 1)
                progress_window.update()

            except Exception as e:
                error_count += 1
                print(f"Error processing {pdf_path}: {e}")

        html_files.sort()

        # PASS 2 — Patch navigation
        for i, name in enumerate(html_files):
            path = os.path.join(output_dir, name)

            prev_file = html_files[i - 1] if i > 0 else None
            next_file = html_files[i + 1] if i < len(html_files) - 1 else None

            try:
                with open(path, "r", encoding="utf-8") as f:
                    html = f.read()

                nav = '<div class="navigation"><div class="nav-buttons">'

                if prev_file:
                    nav += f'<a href="{prev_file}" class="nav-button prev">← Previous</a>'
                else:
                    nav += '<span class="nav-button disabled">← Previous</span>'

                nav += '<a href="index.html" class="nav-button home">Index</a>'

                if next_file:
                    nav += f'<a href="{next_file}" class="nav-button next">Next →</a>'
                else:
                    nav += '<span class="nav-button disabled">Next →</span>'

                nav += '</div></div>'

                html = re.sub(
                    r'<div class="navigation">.*?</div>\s*</div>',
                    nav,
                    html,
                    flags=re.DOTALL
                )

                with open(path, "w", encoding="utf-8") as f:
                    f.write(html)

            except Exception as e:
                print(f"Navigation update failed for {name}: {e}")

        progress_window.destroy()

        messagebox.showinfo(
            "Done",
            f"Processed: {processed_count}\nErrors: {error_count}"
        )

        # Create index.html if we have HTML files
        if html_files:
            index_path = self.create_index_html(html_files, output_dir, processed_count, error_count)
        
        # Close progress window
        progress_window.destroy()
        
        # Show results
        result_msg = f"""
Processing Complete!
Total PDFs found: {len(pdf_files)}
Successfully processed: {processed_count}
Failed: {error_count}

HTML files saved to: {output_dir}
"""
        if html_files:
            result_msg += f"Index file: {index_path}"
        
        messagebox.showinfo("Auto Unredact Complete", result_msg)
        
        # Ask if user wants to open the index file
        if html_files and messagebox.askyesno("Open Index", "Would you like to open the index file in your browser?"):
            import webbrowser
            webbrowser.open(f"file://{index_path}")



    def extract_text_from_pdf(self, pdf_path):
        """Extract all text from a PDF file"""
        text_by_page = {}
        ocr_mode = False
        
        try:
            pdf_doc = fitz.open(pdf_path)
            
            for page_num in range(len(pdf_doc)):
                page = pdf_doc[page_num]
                
                # Check if page has actual text or just images
                text_dict = page.get_text("dict")
                
                # Count text blocks vs image blocks
                text_blocks = sum(1 for block in text_dict.get("blocks", []) if block.get("type") == 0)
                image_blocks = sum(1 for block in text_dict.get("blocks", []) if block.get("type") == 1)
                
                # If mostly/only images, it's OCR mode
                if image_blocks > 0 and text_blocks == 0:
                    ocr_mode = True
                
                # Extract text
                text = page.get_text("text")
                
                if text.strip():
                    text_by_page[page_num + 1] = text.strip()
            
            pdf_doc.close()
            
        except Exception as e:
            print(f"Error extracting text from {pdf_path}: {str(e)}")
        
        return text_by_page, ocr_mode

    def create_html_from_text(self, pdf_path, text_by_page, ocr_mode, output_dir, prev_file=None, next_file=None):
        """Create an HTML file from extracted text with Next/Previous navigation"""
        pdf_name = os.path.basename(pdf_path)
        html_name = os.path.splitext(pdf_name)[0] + ".html"
        html_path = os.path.join(output_dir, html_name)
        
        print(prev_file, next_file)
        
        # Create navigation buttons HTML - ALWAYS create them
        nav_html = """
        <div class="navigation">
            <div class="nav-buttons">
    """
        if prev_file:
            # ALWAYS create Previous button, even if file doesn't exist yet
            nav_html += f"""            <a href="{html.escape(prev_file)}" class="nav-button prev">← Previous File</a>
    """
        else:
            nav_html += f"""            <span class="nav-button disabled">← No Previous</span>
    """
        
        nav_html += f"""            <a href="index.html" class="nav-button home">Index</a>
    """
        
        if next_file:
            # ALWAYS create Next button, even if file doesn't exist yet
            nav_html += f"""            <a href="{html.escape(next_file)}" class="nav-button next">Next File →</a>
    """
        else:
            nav_html += f"""            <span class="nav-button disabled">No Next →</span>
    """
        
        nav_html += """        </div>
        </div>
    """
        
        # Create HTML content
        html_content = f"""<!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Extracted Text: {html.escape(pdf_name)}</title>
        <link rel="stylesheet" type="text/css" href="style.css">
    </head>
    <body>
        <div class="header">
            <h1>Extracted Text: {html.escape(pdf_name)}</h1>
            <p>Original PDF: {html.escape(pdf_path)}</p>
            <p>Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
        </div>
        
        <div class="file-info">
            <p><strong>Source:</strong> {html.escape(pdf_path)}</p>
            <p><strong>Pages:</strong> {len(text_by_page)}</p>
            <p><strong>Extraction Method:</strong> {"OCR (Image-based extraction)" if ocr_mode else "Text layer extraction"}</p>
        </div>
        
        {nav_html}
        
        <div class="sequence-info">
            <p><strong>File Sequence:</strong> {html.escape(pdf_name)}</p>
            <p><strong>Adjacent Files:</strong> 
    """
        
        if prev_file:
            html_content += f"""Previous: <code>{html.escape(prev_file)}</code><br>"""
        if next_file:
            html_content += f"""Next: <code>{html.escape(next_file)}</code>"""
        
        html_content += f"""</p>
        </div>
    """
        
        if ocr_mode is False:
            html_content += """
        <div class="warning">
            <strong>⚠️ WARNING:</strong> This PDF has no text stream - using OCR (may have errors).
            The PDF was converted to images, likely to hide the text layer.
        </div>
    """
        
        # Add each page
        for page_num in sorted(text_by_page.keys()):
            escaped_text = html.escape(text_by_page[page_num])
            html_content += f"""
        <div class="page">
            <div class="page-header">Page {page_num}</div>
            <div class="page-content">{escaped_text}</div>
        </div>
    """
        
        # BOTTOM NAVIGATION (same as top)
        html_content += nav_html
        
        html_content += """
    </body>
    </html>"""
        
        # Write HTML file
        with open(html_path, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        return html_path


    def create_index_html(self, html_files, output_dir, processed_count, error_count):
        """Create an index.html file linking to all HTML files with sequence information"""
        index_path = os.path.join(output_dir, "index.html")
        
        # Sort HTML files by their numerical sequence
        def get_sequence_key(filename):
            base_name = os.path.splitext(filename)[0]
            
            # Find the split between letters and numbers
            split_index = len(base_name)
            for i, char in enumerate(base_name):
                if char.isdigit():
                    split_index = i
                    break
            
            prefix = base_name[:split_index] if split_index > 0 else ""
            number_str = base_name[split_index:] if split_index < len(base_name) else ""
            
            if number_str.isdigit():
                return (prefix, int(number_str))
            return (base_name, 0)
        
        # Make sure we're working with basenames
        html_files = [os.path.basename(f) for f in html_files]
        html_files.sort(key=lambda x: get_sequence_key(x))
        
        # Group files by prefix
        file_groups = {}
        for html_file in html_files:
            filename = html_file
            base_name = os.path.splitext(filename)[0]
            
            # Find the split between letters and numbers
            split_index = len(base_name)
            for i, char in enumerate(base_name):
                if char.isdigit():
                    split_index = i
                    break
            
            prefix = base_name[:split_index] if split_index > 0 else "Other"
            
            if prefix not in file_groups:
                file_groups[prefix] = []
            
            # Store full path for file operations
            full_path = os.path.join(output_dir, filename)
            file_groups[prefix].append({
                'filename': filename,
                'full_path': full_path,
                'basename': base_name
            })
        
        # Create index HTML
        html_content = f"""<!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Extracted PDF Text - Index</title>
        <style>
        body {{
            font-family: Arial, sans-serif;
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
            line-height: 1.6;
            background-color: #f5f5f5;
        }}
        .header {{
            background-color: #2c3e50;
            color: white;
            padding: 20px;
            border-radius: 5px;
            margin-bottom: 20px;
        }}
        .stats {{
            background-color: #e8f4fc;
            padding: 15px;
            border-radius: 5px;
            margin-bottom: 20px;
            display: flex;
            justify-content: space-between;
            flex-wrap: wrap;
        }}
        .stat-box {{
            background-color: white;
            padding: 10px 20px;
            border-radius: 5px;
            margin: 5px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
        }}
        .group {{
            background-color: white;
            padding: 20px;
            border-radius: 5px;
            box-shadow: 0 2px 5px rgba(0,0,0,0.1);
            margin-bottom: 30px;
        }}
        .group-header {{
            background-color: #3498db;
            color: white;
            padding: 10px 15px;
            margin: -20px -20px 20px -20px;
            border-radius: 5px 5px 0 0;
            font-weight: bold;
            font-size: 18px;
        }}
        .file-list {{
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
            gap: 15px;
        }}
        .file-item {{
            padding: 15px;
            border: 1px solid #eee;
            border-radius: 5px;
            background-color: #f8f9fa;
            transition: transform 0.2s, box-shadow 0.2s;
        }}
        .file-item:hover {{
            transform: translateY(-2px);
            box-shadow: 0 4px 8px rgba(0,0,0,0.1);
            background-color: #e8f4fc;
        }}
        .file-name {{
            font-weight: bold;
            color: #2c3e50;
            font-size: 16px;
            margin-bottom: 5px;
        }}
        .view-link {{
            display: inline-block;
            background-color: #27ae60;
            color: white;
            padding: 8px 15px;
            text-decoration: none;
            border-radius: 3px;
            font-size: 14px;
            margin-top: 10px;
        }}
        .view-link:hover {{
            background-color: #229954;
        }}
        .timestamp {{
            color: #666;
            font-size: 12px;
        }}
        .sequence-nav {{
            display: flex;
            justify-content: space-between;
            margin-top: 15px;
            font-size: 12px;
            color: #666;
        }}
        .nav-hint {{
            background-color: #f8f9fa;
            padding: 10px;
            border-radius: 5px;
            margin-bottom: 20px;
            border-left: 4px solid #27ae60;
            font-size: 14px;
        }}
        </style>
    </head>
    <body>
        <div class="header">
            <h1>Extracted PDF Text - Index</h1>
            <p>Browse all extracted text from PDF files with sequential navigation</p>
        </div>
        
        <div class="stats">
            <div class="stat-box">
                <strong>Total Files:</strong> {len(html_files)}
            </div>
            <div class="stat-box">
                <strong>Successfully Processed:</strong> {processed_count}
            </div>
            <div class="stat-box">
                <strong>Failed:</strong> {error_count}
            </div>
            <div class="stat-box">
                <strong>File Groups:</strong> {len(file_groups)}
            </div>
            <div class="stat-box">
                <strong>Generated:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
            </div>
        </div>
        
        <div class="nav-hint">
            <strong>💡 Navigation Tip:</strong> In individual file views, use the Previous/Next buttons at the top and bottom to navigate through sequential files. Files are automatically linked by their numerical sequence (e.g., EFTA0000000001 → EFTA0000000002).
        </div>
    """
        
        # Add each group
        for prefix, files in sorted(file_groups.items()):
            # Sort files within group by their numerical value
            files.sort(key=lambda x: get_sequence_key(x['filename'])[1])
            
            html_content += f"""
        <div class="group">
            <div class="group-header">File Group: {html.escape(prefix)} ({len(files)} files)</div>
            <div class="file-list">
    """
            
            for i, file_info in enumerate(files):
                file_name = file_info['filename']
                file_path = file_info['full_path']
                
                # Get file stats (with error handling in case file doesn't exist)
                try:
                    file_size = os.path.getsize(file_path)
                    modified_time = datetime.fromtimestamp(os.path.getmtime(file_path)).strftime('%Y-%m-%d %H:%M')
                except (FileNotFoundError, OSError):
                    file_size = 0
                    modified_time = "N/A"
                
                # Determine next/previous in sequence for this group
                prev_in_group = files[i-1]['filename'] if i > 0 else None
                next_in_group = files[i+1]['filename'] if i < len(files)-1 else None
                
                html_content += f"""
                <div class="file-item">
                    <div class="file-name">{html.escape(file_name)}</div>
                    <div class="timestamp">
                        Size: {file_size:,} bytes<br>
                        Modified: {modified_time}
                    </div>
    """
                
                if prev_in_group or next_in_group:
                    html_content += f"""            <div class="sequence-nav">
    """
                    if prev_in_group:
                        html_content += f"""                <span>← {html.escape(prev_in_group)}</span>
    """
                    if next_in_group:
                        html_content += f"""                <span>{html.escape(next_in_group)} →</span>
    """
                    html_content += """            </div>
    """
                
                html_content += f"""            <a href="{html.escape(file_name)}" class="view-link">View Extracted Text</a>
                </div>
    """
            
            html_content += """
            </div>
        </div>
    """
        
        html_content += """
    </body>
    </html>"""
        
        # Write index file
        with open(index_path, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        return index_path

    def unredact_all(self):
        """Extract all text from the document (useful for poorly redacted PDFs)"""
        if not self.pdf_doc:
            messagebox.showwarning("Warning", "No PDF loaded")
            return
        
        results_by_page = {}
        ocr_mode = False
        
        # Scan all pages
        for page_num in range(len(self.pdf_doc)):
            page = self.pdf_doc[page_num]
            
            # Check if page has actual text or just images
            text_dict = page.get_text("dict")
            
            # Count text blocks vs image blocks
            text_blocks = sum(1 for block in text_dict.get("blocks", []) if block.get("type") == 0)
            image_blocks = sum(1 for block in text_dict.get("blocks", []) if block.get("type") == 1)
            
            print(f"Page {page_num + 1}: text_blocks={text_blocks}, image_blocks={image_blocks}")
            
            # If mostly/only images, it's OCR mode
            if image_blocks > 0 and text_blocks == 0:
                ocr_mode = True
                print(f"  -> OCR mode detected")
            
            # Extract text (will use OCR if no text layer exists)
            text = page.get_text("text")
            
            if text.strip():
                results_by_page[page_num + 1] = text.strip()
        
        # Display results with warning if OCR was used
        self.show_unredacted_results(results_by_page, ocr_mode)
        
    def show_unredacted_results(self, results_by_page, ocr_mode=False):
        """Show extracted text in a new window"""
        result_window = tk.Toplevel(self.root)
        result_window.title("Extracted Text (Including Under Redactions)")
        result_window.geometry("900x700")
        
        # Add text widget with scrollbar
        text_frame = tk.Frame(result_window)
        text_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        scrollbar = tk.Scrollbar(text_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        text_widget = tk.Text(text_frame, wrap=tk.WORD, yscrollcommand=scrollbar.set, font=("Courier", 9))
        text_widget.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.config(command=text_widget.yview)
        
        # Format and display results
        if results_by_page:
            text_widget.insert(tk.END, f"Extracted text from {len(results_by_page)} pages\n")
            if ocr_mode is False:
                text_widget.insert(tk.END, "⚠️ WARNING: This PDF has no text stream - using OCR (may have errors)\n")
                text_widget.insert(tk.END, "The PDF was converted to images, likely to hide the text layer.\n")
            text_widget.insert(tk.END, "="*80 + "\n\n")
            
            for page_num in sorted(results_by_page.keys()):
                text_widget.insert(tk.END, f"PAGE {page_num}:\n")
                text_widget.insert(tk.END, "-"*80 + "\n")
                text_widget.insert(tk.END, results_by_page[page_num])
                text_widget.insert(tk.END, "\n\n")
        else:
            text_widget.insert(tk.END, "No text found in document.")
        
        text_widget.config(state=tk.DISABLED)
        
        # Add copy all and export buttons
        button_frame = tk.Frame(result_window)
        button_frame.pack(pady=5)
        
        tk.Button(button_frame, text="Copy All to Clipboard", 
                 command=lambda: self.copy_to_clipboard(results_by_page)).pack(side=tk.LEFT, padx=5)
        tk.Button(button_frame, text="Export to File", 
                 command=lambda: self.export_results(results_by_page)).pack(side=tk.LEFT, padx=5)

    def copy_to_clipboard(self, results_by_page):
        """Copy all extracted text to clipboard"""
        all_text = ""
        for page_num in sorted(results_by_page.keys()):
            all_text += f"PAGE {page_num}:\n"
            all_text += "-"*80 + "\n"
            all_text += results_by_page[page_num]
            all_text += "\n\n"
        
        self.root.clipboard_clear()
        self.root.clipboard_append(all_text)
        messagebox.showinfo("Success", "All text copied to clipboard!")

    def export_results(self, results_by_page):
        """Export extracted text to a file"""
        filepath = filedialog.asksaveasfilename(
            title="Export extracted text",
            defaultextension=".txt",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")]
        )
        
        if filepath:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(f"Extracted Text Report - {len(results_by_page)} pages\n")
                f.write("="*80 + "\n\n")
                
                for page_num in sorted(results_by_page.keys()):
                    f.write(f"PAGE {page_num}:\n")
                    f.write("-"*80 + "\n")
                    f.write(results_by_page[page_num])
                    f.write("\n\n")
            
            messagebox.showinfo("Success", f"Exported to {filepath}")

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

### CODE BORROWED - CREDIT: Lee Drake https://www.github.com/leedrake5
    def group_words_into_lines(self, words, line_tol=2.0):
        """Cluster words into lines using their 'top' coordinate."""
        if not words:
            return []

        words = sorted(words, key=lambda w: (float(w.get("top", 0.0)), float(w.get("x0", 0.0))))

        lines = []
        current = []
        current_top = None

        for w in words:
            top = float(w.get("top", 0.0))
            if current_top is None:
                current_top = top
                current = [w]
                continue

            if abs(top - current_top) <= line_tol:
                current.append(w)
                current_top = (current_top * (len(current) - 1) + top) / len(current)
            else:
                lines.append(current)
                current = [w]
                current_top = top

        if current:
            lines.append(current)

        return lines

    def build_line_text(self, line_words, space_unit_pts=3.0, min_spaces=1):
        """Rebuild a line by inserting spaces based on x-gaps."""
        line_words = sorted(line_words, key=lambda w: float(w.get("x0", 0.0)))

        sizes = []
        for w in line_words:
            s = w.get("size", None)
            if s is not None:
                try:
                    sizes.append(float(s))
                except Exception:
                    pass

        if sizes:
            sizes_sorted = sorted(sizes)
            font_size = float(sizes_sorted[len(sizes_sorted) // 2])
        else:
            hs = []
            for w in line_words:
                top = float(w.get("top", 0.0))
                bottom = float(w.get("bottom", top + 10.0))
                hs.append(max(6.0, bottom - top))
            hs.sort()
            font_size = float(hs[len(hs) // 2]) if hs else 10.0

        top_med = sorted([float(w.get("top", 0.0)) for w in line_words])[len(line_words) // 2]

        first_x0 = float(line_words[0].get("x0", 0.0))
        last_x1 = float(line_words[0].get("x1", line_words[0].get("x0", 0.0)))
        prev_x1 = float(line_words[0].get("x1", line_words[0].get("x0", 0.0)))

        parts = [line_words[0].get("text", "")]

        for w in line_words[1:]:
            text = w.get("text", "")
            x0 = float(w.get("x0", 0.0))
            x1 = float(w.get("x1", x0))

            gap = x0 - prev_x1

            if gap > 0:
                n_spaces = int(round(gap / max(0.5, space_unit_pts)))
                n_spaces = max(min_spaces, n_spaces)
                parts.append(" " * n_spaces)
            else:
                parts.append(" " if gap > -space_unit_pts * 0.3 else "")

            parts.append(text)
            prev_x1 = max(prev_x1, x1)
            last_x1 = max(last_x1, x1)

        return "".join(parts), first_x0, last_x1, top_med, font_size

    def extract_lines_with_positions(self, pdf_path, line_tol=2.0, space_unit_pts=3.0, min_spaces=1):
        """Returns list per page: [(line_text, x0, top, font_size), ...]"""
        pages_lines = []

        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                words = page.extract_words(
                    keep_blank_chars=False,
                    use_text_flow=False,
                    extra_attrs=["size", "fontname"]
                )

                lines = self.group_words_into_lines(words, line_tol=line_tol)

                out = []
                for lw in lines:
                    line_text, x0, x1, top, font_size = self.build_line_text(
                        lw, space_unit_pts=space_unit_pts, min_spaces=min_spaces
                    )
                    if line_text.strip():
                        out.append((line_text, x0, top, font_size))
                pages_lines.append(out)

        return pages_lines

    def make_side_by_side(self, input_pdf, output_pdf, line_tol=2.0, space_unit_pts=3.0, min_spaces=1):
        """Create side-by-side PDF: original left, reconstructed text right"""
        src = fitz.open(input_pdf)
        out = fitz.open()

        lines_per_page = self.extract_lines_with_positions(
            input_pdf, line_tol=line_tol, space_unit_pts=space_unit_pts, min_spaces=min_spaces
        )

        for i, src_page in enumerate(src):
            rect = src_page.rect
            w, h = rect.width, rect.height

            new_page = out.new_page(width=2 * w, height=h)

            # Left: embed original page
            new_page.show_pdf_page(fitz.Rect(0, 0, w, h), src, i)

            # Right: draw rebuilt text
            x_off = w
            page_lines = lines_per_page[i] if i < len(lines_per_page) else []

            for (txt, x0, top, font_size) in page_lines:
                y = float(top) + float(font_size) * 0.85

                new_page.insert_text(
                    fitz.Point(x_off + float(x0), float(y)),
                    txt,
                    fontsize=float(font_size),
                    fontname="helv",
                    color=(0, 0, 0),
                    overlay=True
                )

        out.save(output_pdf)
        out.close()
        src.close()

    def make_overlay_white(self, input_pdf, output_pdf, line_tol=2.0, space_unit_pts=3.0, min_spaces=1):
        """Overlay extracted text in white on original PDF"""
        doc = fitz.open(input_pdf)

        lines_per_page = self.extract_lines_with_positions(
            input_pdf, line_tol=line_tol, space_unit_pts=space_unit_pts, min_spaces=min_spaces
        )

        for i, page in enumerate(doc):
            page_lines = lines_per_page[i] if i < len(lines_per_page) else []
            for (txt, x0, top, font_size) in page_lines:
                y = float(top) + float(font_size) * 0.85
                page.insert_text(
                    fitz.Point(float(x0), float(y)),
                    txt,
                    fontsize=float(font_size),
                    fontname="helv",
                    color=(1, 1, 1),   # white
                    overlay=True
                )

        doc.save(output_pdf)
        doc.close()

    def export_side_by_side(self):
        """Add this as a button callback - exports side-by-side comparison"""
        if not self.pdf_doc:
            messagebox.showwarning("Warning", "No PDF loaded")
            return
        
        output_path = filedialog.asksaveasfilename(
            title="Save side-by-side PDF as",
            defaultextension=".pdf",
            filetypes=[("PDF files", "*.pdf")]
        )
        
        if not output_path:
            return
        
        try:
            current_path = self.pdf_doc.name
            self.make_side_by_side(current_path, output_path)
            messagebox.showinfo("Success", f"Side-by-side PDF saved!")
        except Exception as e:
            messagebox.showerror("Error", f"Failed: {str(e)}")

    def export_overlay_white(self):
        """Add this as a button callback - exports white text overlay"""
        if not self.pdf_doc:
            messagebox.showwarning("Warning", "No PDF loaded")
            return
        
        output_path = filedialog.asksaveasfilename(
            title="Save white overlay PDF as",
            defaultextension=".pdf",
            filetypes=[("PDF files", "*.pdf")]
        )
        
        if not output_path:
            return
        
        try:
            current_path = self.pdf_doc.name
            self.make_overlay_white(current_path, output_path)
            messagebox.showinfo("Success", f"White overlay PDF saved!")
        except Exception as e:
            messagebox.showerror("Error", f"Failed: {str(e)}")
### END BORROWED CODE
                    
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

def main():
    root = tk.Tk()
    app = PDFBoxReplacer(root)
    root.mainloop()

if __name__ == "__main__":
    main()
