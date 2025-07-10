# app.py
from flask import Flask, render_template, request, redirect, url_for, send_file, flash
import os
import uuid
import shutil
from utils import generate_storybook_pdf_util # 导入封装的 PDF 生成工具函数
import pandas as pd
from werkzeug.exceptions import RequestEntityTooLarge

app = Flask(__name__)
app.secret_key = 'your_super_secret_key'

# --- 文件上传和大小限制配置 ---
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024 # 50 MB
MAX_SINGLE_IMAGE_SIZE_MB = 5
MAX_SINGLE_IMAGE_SIZE_BYTES = MAX_SINGLE_IMAGE_SIZE_MB * 1024 * 1024

# 定义文件上传和生成PDF的目录
UPLOAD_FOLDER = 'uploads'
GENERATED_PDFS_FOLDER = 'generated_pdfs'
IMAGES_TEMP_FOLDER = 'images_temp'
FONTS_FOLDER = 'fonts'
EXAMPLE_FILES_FOLDER = 'examples'

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(GENERATED_PDFS_FOLDER, exist_ok=True)
os.makedirs(IMAGES_TEMP_FOLDER, exist_ok=True)
os.makedirs(FONTS_FOLDER, exist_ok=True)
os.makedirs(EXAMPLE_FILES_FOLDER, exist_ok=True)

ALLOWED_CSV_EXTENSIONS = {'csv'}
ALLOWED_IMAGE_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

def allowed_file(filename, allowed_extensions):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in allowed_extensions

@app.route('/', methods=['GET'])
def index():
    pdf_to_download = request.args.get('download_pdf')
    if pdf_to_download:
        pdf_path = os.path.join(GENERATED_PDFS_FOLDER, pdf_to_download)
        if os.path.exists(pdf_path):
            response = send_file(pdf_path, as_attachment=True, download_name="你的绘本.pdf")
            @response.call_on_close
            def cleanup():
                try:
                    os.remove(pdf_path)
                    print(f"已清理生成的PDF文件: {pdf_path}")
                except Exception as e:
                    print(f"清理PDF文件 '{pdf_path}' 时出错: {e}")
            return response
        else:
            flash("下载文件不存在或已过期。")
    return render_template('index.html')

@app.route('/download_example_csv', methods=['GET'])
def download_example_csv():
    example_csv_path = os.path.join(EXAMPLE_FILES_FOLDER, 'example.csv')
    if not os.path.exists(example_csv_path):
        flash("示例CSV文件不存在，请联系管理员。")
        return redirect(url_for('index'))
    
    return send_file(example_csv_path, as_attachment=True, download_name="example.csv")

@app.route('/generate', methods=['POST'])
def generate_storybook():
    session_id = str(uuid.uuid4())
    temp_upload_dir = os.path.join(UPLOAD_FOLDER, session_id)
    temp_image_dir = os.path.join(temp_upload_dir, IMAGES_TEMP_FOLDER)
    csv_filepath = None

    try:
        if 'csv_file' not in request.files:
            flash('未上传 CSV 文件。')
            return redirect(request.url)
        
        csv_file = request.files['csv_file']
        image_files = request.files.getlist('image_files')

        # --- 新增：获取样式和布局选项 ---
        font_style = request.form.get('font_style', 'msyh') # 默认微软雅黑
        color_theme = request.form.get('color_theme', 'eye_friendly') # 默认护眼绿
        layout_style = request.form.get('layout_style', 'image_top_text_bottom') # 默认图片在上文字在下
        print(f"用户选择的选项 - 字体: {font_style}, 主题: {color_theme}, 布局: {layout_style}")
        # --- 获取选项结束 ---

        if csv_file.filename == '':
            flash('CSV 文件名为空。')
            return redirect(request.url)

        if not allowed_file(csv_file.filename, ALLOWED_CSV_EXTENSIONS):
            flash('不支持的 CSV 文件类型。只允许 .csv 文件。')
            return redirect(request.url)

        if not image_files or all(f.filename == '' for f in image_files):
            flash('未上传图片文件。')
            return redirect(request.url)
        
        for img_file in image_files:
            if not allowed_file(img_file.filename, ALLOWED_IMAGE_EXTENSIONS):
                flash(f'不支持的图片文件类型: {img_file.filename}。只允许 .png, .jpg, .jpeg, .gif 文件。')
                return redirect(request.url)
            if img_file.content_length > MAX_SINGLE_IMAGE_SIZE_BYTES:
                flash(f'图片 "{img_file.filename}" 大小超过了单张图片限制 ({MAX_SINGLE_IMAGE_SIZE_MB}MB)。')
                return redirect(request.url)

        os.makedirs(temp_image_dir, exist_ok=True)

        csv_filepath = os.path.join(temp_upload_dir, csv_file.filename)
        csv_file.save(csv_filepath)
        print(f"CSV文件保存至: {csv_filepath}")

        try:
            df_temp = pd.read_csv(csv_filepath, header=None, delimiter=';', encoding='utf-8')
            expected_image_count = len(df_temp)
        except Exception as e:
            flash(f"读取 CSV 文件失败，请检查格式 (无标题行，分号分隔，UTF-8编码): {e}")
            return redirect(request.url)

        if len(image_files) != expected_image_count:
            flash(f'图片数量与CSV文件行数不匹配。CSV有 {expected_image_count} 行，但上传了 {len(image_files)} 张图片。')
            return redirect(request.url)

        saved_image_count = 0
        for i, img_file in enumerate(image_files):
            ext = img_file.filename.rsplit('.', 1)[1].lower() if '.' in img_file.filename else 'png'
            image_save_path = os.path.join(temp_image_dir, f"{i+1}.{ext}")
            img_file.save(image_save_path)
            print(f"图片保存至: {image_save_path}")
            saved_image_count += 1
        print(f"成功保存 {saved_image_count} 张图片。")

        pdf_filename = f"storybook_{session_id}.pdf"
        output_pdf_filepath = os.path.join(GENERATED_PDFS_FOLDER, pdf_filename)

        print("开始生成 PDF...")
        # --- 修改：将样式和布局选项传递给工具函数 ---
        success = generate_storybook_pdf_util(
            csv_filepath, 
            temp_image_dir, 
            output_pdf_filepath,
            font_style=font_style,
            color_theme=color_theme,
            layout_style=layout_style
        )
        # --- 传递选项结束 ---

        if success:
            flash('绘本PDF已成功生成，即将开始下载。')
            return redirect(url_for('index', download_pdf=pdf_filename))
        else:
            flash('绘本PDF生成失败，请检查文件格式或重试。')
            if os.path.exists(output_pdf_filepath):
                os.remove(output_pdf_filepath)
            return redirect(url_for('index'))

    except RequestEntityTooLarge:
        flash(f'上传的文件总大小超过了限制 ({app.config["MAX_CONTENT_LENGTH"] / (1024 * 1024):.0f}MB)。')
        return redirect(request.url)
    except Exception as e:
        print(f"处理请求时发生未知错误: {e}")
        flash(f"生成绘本时发生未知错误: {e}")
        return redirect(url_for('index'))
    finally:
        if os.path.exists(temp_upload_dir):
            try:
                shutil.rmtree(temp_upload_dir)
                print(f"已清理临时上传目录: {temp_upload_dir}")
            except OSError as e:
                print(f"清理临时目录 '{temp_upload_dir}' 时出错: {e}")

if __name__ == '__main__':
    font_source_path_msyh = 'STHeiti Light.ttc'
    font_dest_path_msyh = os.path.join(FONTS_FOLDER, 'STHeiti Light.ttc')
    if not os.path.exists(font_dest_path_msyh):
        if os.path.exists(font_source_path_msyh):
            shutil.copy(font_source_path_msyh, font_dest_path_msyh)
            print(f"字体文件 '{font_source_path_msyh}' 已复制到 '{font_dest_path_msyh}'")
        else:
            print(f"警告: 微软雅黑字体文件 '{font_source_path_msyh}' 未找到。请将其放置在项目根目录或 '{FONTS_FOLDER}' 目录中。中文显示可能出现问题。")

    font_source_path_simsun = 'PingFang.ttc' # 注意：宋体通常是 .ttc
    font_dest_path_simsun = os.path.join(FONTS_FOLDER, 'PingFang.ttc')
    if not os.path.exists(font_dest_path_simsun):
        if os.path.exists(font_source_path_simsun):
            shutil.copy(font_source_path_simsun, font_dest_path_simsun)
            print(f"字体文件 '{font_source_path_simsun}' 已复制到 '{font_dest_path_simsun}'")
        else:
            print(f"警告: 宋体字体文件 '{font_source_path_simsun}' 未找到。请将其放置在项目根目录或 '{FONTS_FOLDER}' 目录中。宋体显示将不可用。")

    example_csv_src = 'example.csv'
    example_csv_dest = os.path.join(EXAMPLE_FILES_FOLDER, 'example.csv')
    if not os.path.exists(example_csv_dest):
        if os.path.exists(example_csv_src):
            shutil.copy(example_csv_src, example_csv_dest)
            print(f"示例CSV文件 '{example_csv_src}' 已复制到 '{example_csv_dest}'")
        else:
            print(f"警告: 示例CSV文件 '{example_csv_src}' 未找到。请将其放置在项目根目录或 '{EXAMPLE_FILES_FOLDER}' 目录中。")

    app.run(debug=True, port=5000)