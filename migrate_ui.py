import os
import shutil
import glob

base_dir = r"c:\Users\radhe\OneDrive\Desktop\FRS\Face-Recognition-System\attendance_ai"
frontend_dir = os.path.join(base_dir, "frontend")
backend_dir = os.path.join(base_dir, "backend")

templates_dir = os.path.join(backend_dir, "templates")
static_dir = os.path.join(backend_dir, "static")

# Create dirs
os.makedirs(templates_dir, exist_ok=True)
os.makedirs(static_dir, exist_ok=True)

# 1. Move CSS and JS
for assets in ["css", "js", "img", "images", "assets"]:
    src_path = os.path.join(frontend_dir, assets)
    dst_path = os.path.join(static_dir, assets)
    if os.path.exists(src_path):
        if os.path.exists(dst_path):
            shutil.rmtree(dst_path)
        shutil.copytree(src_path, dst_path)
        print(f"Moved {assets} to {dst_path}")

# 2. Process and Move HTML files
html_files = glob.glob(os.path.join(frontend_dir, "*.html"))
for html_file in html_files:
    filename = os.path.basename(html_file)
    dst_path = os.path.join(templates_dir, filename)
    
    with open(html_file, 'r', encoding='utf-8') as f:
        content = f.read()
        
    # Replace references
    # Example: href="/css/style.css" -> href="/static/css/style.css"
    content = content.replace('href="/css/', 'href="/static/css/')
    content = content.replace('src="/js/', 'src="/static/js/')
    content = content.replace('href="css/', 'href="/static/css/')
    content = content.replace('src="js/', 'src="/static/js/')
    content = content.replace("href='/css/", "href='/static/css/")
    content = content.replace("src='/js/", "src='/static/js/")
    content = content.replace("href='css/", "href='/static/css/")
    content = content.replace("src='js/", "src='/static/js/")
    
    with open(dst_path, 'w', encoding='utf-8') as f:
        f.write(content)
    print(f"Processed and moved {filename} to {dst_path}")

print("Migration script completed successfully!")
