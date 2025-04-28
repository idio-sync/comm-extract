import os
import re
import subprocess
import tkinter as tk
from tkinter import filedialog, ttk
import threading
import json

class CommentaryExtractorApp:
    def __init__(self, root):
        self.root = root
        root.title("Commentary Track Extractor")
        root.geometry("700x500")
        root.minsize(600, 400)
        
        # Configure root grid
        root.columnconfigure(0, weight=1)
        root.rowconfigure(0, weight=1)
        
        # Main frame
        main_frame = ttk.Frame(root, padding="10")
        main_frame.grid(row=0, column=0, sticky="nsew")
        main_frame.columnconfigure(0, weight=1)
        main_frame.rowconfigure(3, weight=1)
        
        # Directory selection frames
        input_frame = ttk.LabelFrame(main_frame, text="Input Directory", padding="5")
        input_frame.grid(row=0, column=0, sticky="ew", pady=5)
        input_frame.columnconfigure(0, weight=1)
        
        output_frame = ttk.LabelFrame(main_frame, text="Output Directory", padding="5")
        output_frame.grid(row=1, column=0, sticky="ew", pady=5)
        output_frame.columnconfigure(0, weight=1)
        
        # Input directory widgets
        self.input_dir = tk.StringVar()
        input_entry = ttk.Entry(input_frame, textvariable=self.input_dir)
        input_entry.grid(row=0, column=0, sticky="ew", padx=5)
        
        input_button = ttk.Button(input_frame, text="Browse...", command=self.select_input_dir)
        input_button.grid(row=0, column=1, padx=5)
        
        # Output directory widgets
        self.output_dir = tk.StringVar()
        output_entry = ttk.Entry(output_frame, textvariable=self.output_dir)
        output_entry.grid(row=0, column=0, sticky="ew", padx=5)
        
        output_button = ttk.Button(output_frame, text="Browse...", command=self.select_output_dir)
        output_button.grid(row=0, column=1, padx=5)
        
        # Commentary detection options frame
        options_frame = ttk.LabelFrame(main_frame, text="Commentary Detection Options", padding="5")
        options_frame.grid(row=2, column=0, sticky="ew", pady=5)
        
        # Commentary keywords entry
        ttk.Label(options_frame, text="Keywords to identify commentary tracks (comma separated):").grid(row=0, column=0, sticky="w", padx=5, pady=2)
        self.commentary_keywords = tk.StringVar(value="commentary,director,filmmaker,crew,discussion,chat")
        keywords_entry = ttk.Entry(options_frame, textvariable=self.commentary_keywords)
        keywords_entry.grid(row=1, column=0, sticky="ew", padx=5, pady=2)
        
        # Action buttons
        buttons_frame = ttk.Frame(main_frame)
        buttons_frame.grid(row=4, column=0, sticky="ew", pady=10)
        buttons_frame.columnconfigure(0, weight=1)
        buttons_frame.columnconfigure(1, weight=1)
        
        self.scan_button = ttk.Button(buttons_frame, text="Scan and Extract", command=self.start_extraction)
        self.scan_button.grid(row=0, column=0, sticky="e", padx=5)
        
        self.cancel_button = ttk.Button(buttons_frame, text="Cancel", command=self.cancel_extraction, state="disabled")
        self.cancel_button.grid(row=0, column=1, sticky="w", padx=5)
        
        # Log frame
        log_frame = ttk.LabelFrame(main_frame, text="Log", padding="5")
        log_frame.grid(row=3, column=0, sticky="nsew", pady=5)
        log_frame.rowconfigure(0, weight=1)
        log_frame.columnconfigure(0, weight=1)
        
        # Log text widget with scrollbar
        self.log_text = tk.Text(log_frame, wrap="word", height=10)
        self.log_text.grid(row=0, column=0, sticky="nsew")
        
        scrollbar = ttk.Scrollbar(log_frame, orient="vertical", command=self.log_text.yview)
        scrollbar.grid(row=0, column=1, sticky="ns")
        self.log_text.configure(yscrollcommand=scrollbar.set)
        
        # Status bar
        self.status_var = tk.StringVar(value="Ready")
        status_bar = ttk.Label(main_frame, textvariable=self.status_var, relief=tk.SUNKEN, anchor="w")
        status_bar.grid(row=5, column=0, sticky="ew")
        
        # Thread control
        self.running = False
        self.extraction_thread = None
        
    def select_input_dir(self):
        directory = filedialog.askdirectory()
        if directory:
            self.input_dir.set(directory)
            
    def select_output_dir(self):
        directory = filedialog.askdirectory()
        if directory:
            self.output_dir.set(directory)
    
    def log(self, message):
        self.log_text.insert(tk.END, message + "\n")
        self.log_text.see(tk.END)
        self.root.update_idletasks()
        
    def update_status(self, message):
        self.status_var.set(message)
        self.root.update_idletasks()
        
    def start_extraction(self):
        if not self.input_dir.get() or not self.output_dir.get():
            self.log("Error: Please select both input and output directories.")
            return
            
        if not os.path.exists(self.input_dir.get()) or not os.path.isdir(self.input_dir.get()):
            self.log(f"Error: Input directory '{self.input_dir.get()}' does not exist or is not a directory.")
            return
            
        if not os.path.exists(self.output_dir.get()):
            try:
                os.makedirs(self.output_dir.get())
            except Exception as e:
                self.log(f"Error creating output directory: {str(e)}")
                return
                
        # Check if MKVToolNix is installed
        try:
            # Use subprocess.check_output instead of run for more reliable capture
            subprocess.check_output(["mkvinfo", "--version"], stderr=subprocess.STDOUT, text=True)
        except (subprocess.SubprocessError, FileNotFoundError) as e:
            self.log("Error: MKVToolNix is not installed or not in the PATH.")
            self.log(f"Details: {str(e)}")
            self.log("Please install MKVToolNix from https://mkvtoolnix.download/")
            return
            
        # Update UI
        self.scan_button.configure(state="disabled")
        self.cancel_button.configure(state="normal")
        self.running = True
        
        # Start extraction in a separate thread
        self.extraction_thread = threading.Thread(target=self.run_extraction)
        self.extraction_thread.daemon = True
        self.extraction_thread.start()
        
    def cancel_extraction(self):
        if self.running and self.extraction_thread and self.extraction_thread.is_alive():
            self.running = False
            self.log("Cancelling extraction process...")
            self.update_status("Cancelling...")
            
    def run_extraction(self):
        try:
            self.update_status("Scanning for movie folders...")
            self.log(f"Starting scan of {self.input_dir.get()}")
            
            # Get all immediate subdirectories (movie folders)
            movie_dirs = [d for d in os.listdir(self.input_dir.get()) 
                         if os.path.isdir(os.path.join(self.input_dir.get(), d))]
            
            self.log(f"Found {len(movie_dirs)} movie folders")
            
            # Get keywords for commentary detection
            keywords = [k.strip().lower() for k in self.commentary_keywords.get().split(",")]
            
            if not keywords:
                self.log("Warning: No commentary keywords specified. Using default 'commentary'.")
                keywords = ["commentary"]
                
            self.log(f"Using keywords for detection: {', '.join(keywords)}")
            
            for i, movie_dir in enumerate(movie_dirs):
                if not self.running:
                    break
                    
                full_movie_path = os.path.join(self.input_dir.get(), movie_dir)
                self.update_status(f"Processing {i+1}/{len(movie_dirs)}: {movie_dir}")
                self.log(f"\nProcessing movie folder: {movie_dir}")
                
                # Find MKV files
                mkv_files = [f for f in os.listdir(full_movie_path) 
                            if f.lower().endswith(".mkv") and os.path.isfile(os.path.join(full_movie_path, f))]
                
                if not mkv_files:
                    self.log(f"  No MKV files found in {movie_dir}")
                    continue
                    
                self.log(f"  Found {len(mkv_files)} MKV files")
                
                for mkv_file in mkv_files:
                    if not self.running:
                        break
                        
                    full_mkv_path = os.path.join(full_movie_path, mkv_file)
                    self.log(f"  Analyzing: {mkv_file}")
                    
                    # Get track info using mkvmerge - FIXED ERROR HANDLING HERE
                    try:
                        # Use check_output instead of run for better stdout capture
                        output = subprocess.check_output(
                            ["mkvmerge", "-J", full_mkv_path], 
                            stderr=subprocess.STDOUT,
                            text=True
                        )
                        
                        # Make sure we have output before trying to parse it
                        if not output:
                            self.log(f"    Error: mkvmerge returned empty output")
                            continue
                            
                        try:
                            track_info = json.loads(output)
                        except json.JSONDecodeError as e:
                            self.log(f"    Error parsing mkvmerge output: {str(e)}")
                            self.log(f"    First 100 chars of output: {output[:100]}...")
                            continue
                            
                    except subprocess.CalledProcessError as e:
                        self.log(f"    Error analyzing file: {str(e)}")
                        if e.output:
                            self.log(f"    Command output: {e.output[:200]}...")
                        continue
                    except Exception as e:
                        self.log(f"    Unexpected error analyzing file: {str(e)}")
                        continue
                        
                    # Find audio tracks
                    audio_tracks = []
                    for track in track_info.get("tracks", []):
                        if track.get("type") == "audio":
                            track_id = track.get("id")
                            properties = track.get("properties", {})
                            
                            # Get track name and language
                            track_name = properties.get("track_name", "")
                            language = properties.get("language", "")
                            codec = properties.get("codec_id", "").split("/")[-1]
                            
                            # Check if it's a commentary track
                            is_commentary = False
                            track_name_lower = track_name.lower()
                            for keyword in keywords:
                                if keyword in track_name_lower:
                                    is_commentary = True
                                    break
                                    
                            if is_commentary:
                                # Determine file extension based on codec
                                ext = "mka"  # Default fallback
                                if codec.startswith("A_AC3"):
                                    ext = "ac3"
                                elif codec.startswith("A_AAC"):
                                    ext = "aac"
                                elif codec.startswith("A_MP3"):
                                    ext = "mp3"
                                elif codec.startswith("A_DTS"):
                                    ext = "dts"
                                elif codec.startswith("A_PCM"):
                                    ext = "wav"
                                elif codec.startswith("A_FLAC"):
                                    ext = "flac"
                                    
                                audio_tracks.append({
                                    "id": track_id,
                                    "name": track_name or f"Commentary Track {track_id}",
                                    "language": language,
                                    "codec": codec,
                                    "extension": ext
                                })
                    
                    if not audio_tracks:
                        self.log(f"    No commentary tracks found")
                        continue
                        
                    self.log(f"    Found {len(audio_tracks)} commentary tracks")
                    
                    # Extract each commentary track
                    for track in audio_tracks:
                        if not self.running:
                            break
                            
                        track_id = track["id"]
                        track_name = track["name"]
                        extension = track["extension"]
                        
                        # Create a valid filename
                        safe_movie_name = re.sub(r'[<>:"/\\|?*]', '_', movie_dir)
                        safe_track_name = re.sub(r'[<>:"/\\|?*]', '_', track_name)
                        output_filename = f"{safe_movie_name} - {safe_track_name}.{extension}"
                        output_path = os.path.join(self.output_dir.get(), output_filename)
                        
                        self.log(f"    Extracting track '{track_name}' to '{output_filename}'")
                        
                        try:
                            # Extract the track using mkvextract
                            # Don't use check_output here since we want to see the error output
                            result = subprocess.run(
                                ["mkvextract", "tracks", full_mkv_path, f"{track_id}:{output_path}"],
                                capture_output=True,
                                text=True
                            )
                            
                            if result.returncode == 0:
                                self.log(f"      Extraction successful")
                            else:
                                self.log(f"      Extraction failed: {result.stderr}")
                        except Exception as e:
                            self.log(f"      Extraction error: {str(e)}")
            
            if self.running:
                self.log("\nExtraction process completed successfully!")
                self.update_status("Done")
            else:
                self.log("\nExtraction process was cancelled.")
                self.update_status("Cancelled")
                
        except Exception as e:
            self.log(f"Error during extraction process: {str(e)}")
            self.update_status("Error")
            
        finally:
            self.running = False
            self.scan_button.configure(state="normal")
            self.cancel_button.configure(state="disabled")
            
if __name__ == "__main__":
    root = tk.Tk()
    app = CommentaryExtractorApp(root)
    root.mainloop()