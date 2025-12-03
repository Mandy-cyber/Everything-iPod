#--------------------------------------------------------------------------------------
# SOURCE: https://github.com/Xpl0itU/rockbox_scripts/blob/master/album_art_fix.py
# I've done nothing to this code except remove unused imports. Full credit to XploitU!
#--------------------------------------------------------------------------------------
import os
import shutil
import tempfile
import base64
from PIL import Image, UnidentifiedImageError
from mutagen import File
from mutagen.flac import Picture as FLACPicture, error as FLACError # Renamed Picture
from mutagen.mp4 import MP4, MP4Cover

SUPPORTED_EXTENSIONS = (".mp3", ".flac", ".opus", ".ogg", ".m4a")
IMAGE_EXTENSIONS = (".jpg", ".jpeg", ".png")
COVER_FILENAME = "cover.jpg"
TEMP_FOLDER_NAME = "cover_extraction_temp" # Used by clear_temp_directory and new extract_art_mutagen

# Existing functions...

def extract_art_mutagen(file_path: str) -> str | None:
    try:
        # Use easy=False for detailed object, or easy=True if simpler access is preferred and sufficient
        file_obj = File(file_path, easy=False)
        if file_obj is None:
            print(f"Could not load file with mutagen: {file_path}")
            return None

        pictures_data = [] # List to hold {'data': bytes, 'mime': str}
        file_ext = os.path.splitext(file_path)[1].lower()

        if file_ext == ".mp3":
            if hasattr(file_obj, 'tags') and file_obj.tags:
                for key in file_obj.tags.keys():
                    if key.startswith("APIC:"):
                        apic_frame = file_obj.tags[key]
                        pictures_data.append({'data': apic_frame.data, 'mime': apic_frame.mime})
                        break # Take the first APIC frame
        elif file_ext == ".flac":
            if hasattr(file_obj, 'pictures') and file_obj.pictures:
                for pic in file_obj.pictures:
                    pictures_data.append({'data': pic.data, 'mime': pic.mime})
                    break # Take the first picture
        elif file_ext in (".opus", ".ogg"):
            # Opus stores pictures in METADATA_BLOCK_PICTURE Vorbis comments, often base64 encoded FLAC Picture blocks
            if hasattr(file_obj, 'tags') and file_obj.tags:
                # Look for list-type tags first
                b64_picture_tags = []
                if isinstance(file_obj.tags.get('METADATA_BLOCK_PICTURE'), list):
                    b64_picture_tags.extend(file_obj.tags.get('METADATA_BLOCK_PICTURE'))
                elif isinstance(file_obj.tags.get('METADATA_BLOCK_PICTURE'), str):
                    b64_picture_tags.append(file_obj.tags.get('METADATA_BLOCK_PICTURE'))

                for b64_data in b64_picture_tags:
                    try:
                        pic_data_bytes = base64.b64decode(b64_data)
                        # Attempt to parse as a FLAC Picture block to get mime type and actual data
                        flac_pic = FLACPicture(pic_data_bytes)
                        pictures_data.append({'data': flac_pic.data, 'mime': flac_pic.mime})
                        break # Found and parsed one
                    except (TypeError, ValueError, base64.binascii.Error, FLACError) as e:
                        # print(f"Could not parse Opus picture data from {file_path}: {e}")
                        continue
        elif file_ext == ".m4a":
            # M4A (MP4 audio) cover extraction
            try:
                mp4_obj = MP4(file_path)
                covr = mp4_obj.tags.get("covr")
                if covr:
                    cover_obj = covr[0]
                    if isinstance(cover_obj, MP4Cover):
                        # Determine MIME type by cover_obj.imageformat
                        # 13 is JPEG, 14 is PNG (see mutagen.mp4.MP4Cover)
                        mime = "image/jpeg" if cover_obj.imageformat == MP4Cover.FORMAT_JPEG else "image/png"
                        pictures_data.append({'data': cover_obj, 'mime': mime})
            except Exception as e:
                print(f"Error extracting cover from M4A: {file_path}: {e}")

        if not pictures_data:
            # print(f"No embedded art found in {file_path} using mutagen.") # Reduce verbosity
            return None

        selected_picture = pictures_data[0]
        pic_data_bytes = selected_picture['data']
        mime_type = selected_picture['mime']

        extensions = {"image/jpeg": "jpeg", "image/png": "png", "image/gif": "gif"}
        ext = extensions.get(mime_type, "jpeg")

        # Save to a temporary path before processing
        temp_extraction_dir = os.path.join(tempfile.gettempdir(), TEMP_FOLDER_NAME + "_extract")
        os.makedirs(temp_extraction_dir, exist_ok=True)

        temp_art_filename = os.path.splitext(os.path.basename(file_path))[0] + f".{ext}"
        temp_art_path = os.path.join(temp_extraction_dir, temp_art_filename)

        with open(temp_art_path, "wb") as h:
            h.write(pic_data_bytes)

        # print(f"Album art extracted from {file_path} to {temp_art_path}")
        process_cover_image(temp_art_path) # This modifies in-place, converts to JPEG

        # The file at temp_art_path is now a JPEG image, 200x200.
        return temp_art_path

    except Exception as e:
        print(f"Error extracting art from {file_path} with mutagen: {e}")
        return None

def handle_audio_files(directory: str, temp_folder: str):
    # temp_folder is no longer strictly needed by this func but kept for signature consistency
    audio_files = [
        os.path.join(directory, f) for f in os.listdir(directory)
        if f.endswith(SUPPORTED_EXTENSIONS)
    ]

    for audio_file_path in audio_files: # Iterate through all supported audio files
        # print(f"Attempting to extract art from {audio_file_path} using mutagen.")
        # The temp_folder argument to extract_art_mutagen is implicitly handled by its use of tempfile.gettempdir()
        cover_path = extract_art_mutagen(audio_file_path)

        if cover_path:
            final_cover_dest = os.path.join(directory, COVER_FILENAME)
            shutil.move(cover_path, final_cover_dest)
            print(f"Cover image extracted from {os.path.basename(audio_file_path)} using mutagen, processed, and saved as {COVER_FILENAME} in {directory}")
            return # Found cover for this directory, exit

    # print(f"No cover art found for directory {directory} using mutagen.") # Reduce verbosity


def sanitize_filename(filename: str): # Added from original script, was missing in user's version
    return "".join(
        c if c.isalnum() or c in [".", "_", "-", " "] else "_" for c in filename
    )

def get_album_tag(file_path: str): # Added from original script, was missing in user's version
    try:
        if file_path.endswith(SUPPORTED_EXTENSIONS):
            album_tag = File(file_path, easy=True)["album"]
            return album_tag[0] if isinstance(album_tag, list) else album_tag
    except Exception as e:
        print(f"Error reading metadata for {file_path}: {e}")
        return None

def organize_music_files(root_dir: str):
    for filename in os.listdir(root_dir):
        file_path = os.path.join(root_dir, filename)

        if os.path.isfile(file_path) and file_path.endswith(SUPPORTED_EXTENSIONS):
            album_tag = get_album_tag(file_path)

            if album_tag:
                sanitized_album_tag = sanitize_filename(str(album_tag))
                album_folder = os.path.join(root_dir, sanitized_album_tag)
                if not os.path.exists(album_folder):
                    os.makedirs(album_folder)

                try:
                    shutil.move(file_path, os.path.join(album_folder, filename))
                    print(f"Moved '{filename}' to '{sanitized_album_tag}' folder.")
                except Exception as e:
                    print(f"Error moving '{filename}': {e}")

def process_cover_image(image_path: str):
    try:
        with Image.open(image_path) as img:
            img = img.convert("RGB")
            img = img.resize((200, 200))
            img.save(image_path, "JPEG", quality=100, subsampling=0)
            print(
                f"Modified '{os.path.basename(image_path)}' in {os.path.dirname(image_path)}"
            )
    except UnidentifiedImageError as e:
        print(f"Error processing '{os.path.basename(image_path)}': {str(e)}")

def process_images(root_dir: str):
    processed_folders = set()
    try:
        folders_processed = 0

        for root, dirs, _ in os.walk(root_dir):
            if ".rockbox" in dirs:
                dirs.remove(".rockbox")

            cover_path = os.path.join(root, COVER_FILENAME)

            if root in processed_folders:
                continue

            if os.path.exists(cover_path) and os.path.getsize(cover_path) > 0:
                print(f"\nProcessing folder: {root}")
                process_cover_image(cover_path)
            else:
                handle_audio_files(
                    root,
                    os.path.join(tempfile.gettempdir(), TEMP_FOLDER_NAME),
                )
                folders_processed += 1
                processed_folders.add(root)

        if folders_processed > 0:
            print(f"\n{folders_processed} folder(s) processed.")
        else:
            print("\nNo folders to process. Exiting.")

    except KeyboardInterrupt:
        print("\nProcessing interrupted by user.")

def clear_temp_directory():
    temp_folder = tempfile.gettempdir()
    temp_folder_path = os.path.join(temp_folder, TEMP_FOLDER_NAME)

    if os.path.exists(temp_folder_path):
        shutil.rmtree(temp_folder_path)
        print(f"Cleared directory: {temp_folder_path}")
    else:
        print(f"Directory does not exist: {temp_folder_path}")

def main(root_directory: str) -> None:
    organize_music_files(root_directory)
    process_images(root_directory)
    clear_temp_directory()

if __name__ == "__main__":
    import typer

    typer.run(main)