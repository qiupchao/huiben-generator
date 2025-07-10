# utils.py
import pandas as pd
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import Paragraph, Spacer
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.lib.colors import Color, black, white
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
import os
import math

def generate_storybook_pdf_util(data_file_path, uploaded_image_dir, output_pdf_path, 
                                font_style='msyh', color_theme='eye_friendly', layout_style='image_top_text_bottom'):
    """
    根据提供的数据文件和图片目录生成绘本PDF。
    现在支持字体、颜色主题和布局的定制。

    Args:
        data_file_path (str): 包含单词和小句的数据文件路径 (CSV)。
        uploaded_image_dir (str): 用户上传图片临时存放的目录。
        output_pdf_path (str): 生成的PDF文件的输出路径和名称。
        font_style (str): 字体样式，'msyh' (微软雅黑) 或 'simsun' (宋体)。
        color_theme (str): 颜色主题，'eye_friendly' (护眼绿) 或 'classic_white' (经典白)。
    Returns:
        bool: 如果PDF成功生成返回 True，否则返回 False。
    """
    try:
        df = pd.read_csv(data_file_path, header=None, names=['word', 'sentence'], delimiter=';', encoding='utf-8')
        print(f"成功读取数据文件：{data_file_path}，共 {len(df)} 条数据。")
    except FileNotFoundError:
        print(f"错误：找不到数据文件 '{data_file_path}'。")
        return False
    except Exception as e:
        print(f"读取数据文件时发生错误：{e}")
        return False

    c = canvas.Canvas(output_pdf_path, pagesize=letter)
    width, height = letter

    # --- 注册中文字体 ---
    # 定义字体映射
    FONT_MAP = {
        'STHeiti': {"name": "STHeiti", "path": "STHeiti Light.ttc"}, # 微软雅黑
        'PingFang': {"name": "PingFang", "path": "PingFang.ttc"} # 宋体
    }

    selected_font_info = FONT_MAP.get(font_style, FONT_MAP['STHeiti']) # 默认微软雅黑
    FONT_NAME_CHINESE = selected_font_info["name"]
    FONT_PATH_CHINESE = os.path.join(os.path.dirname(__file__), 'fonts', selected_font_info["path"])

    if not os.path.exists(FONT_PATH_CHINESE):
        print(f"错误：中文字体文件 '{FONT_PATH_CHINESE}' 不存在。请确保字体文件放置正确。")
        return False

    try:
        pdfmetrics.registerFont(TTFont(FONT_NAME_CHINESE, FONT_PATH_CHINESE))
        print(f"成功注册中文字体：{FONT_NAME_CHINESE}")
    except Exception as e:
        print(f"错误：无法注册中文字体 '{FONT_PATH_CHINESE}'。错误信息：{e}")
        return False

    # --- 定义颜色主题 ---
    if color_theme == 'eye_friendly':
        BACKGROUND_COLOR = Color(red=220/255, green=230/255, blue=240/255)
        WORD_TEXT_COLOR = '#333333'
        SENTENCE_TEXT_COLOR = '#666666'
    else: # classic_white
        BACKGROUND_COLOR = white
        WORD_TEXT_COLOR = black
        SENTENCE_TEXT_COLOR = '#333333'

    # 定义文本样式
    styles = getSampleStyleSheet()
    word_style = ParagraphStyle(
        'WordStyle',
        parent=styles['Normal'],
        fontName=FONT_NAME_CHINESE, 
        fontSize=48,
        alignment=TA_CENTER,
        spaceAfter=40,
        leading=58, 
        textColor=WORD_TEXT_COLOR
    )
    sentence_style = ParagraphStyle(
        'SentenceStyle',
        parent=styles['Normal'],
        fontName=FONT_NAME_CHINESE, 
        fontSize=24,
        alignment=TA_CENTER,
        spaceAfter=50, 
        leading=30, 
        textColor=SENTENCE_TEXT_COLOR
    )

    # 2. 每条数据创建一个绘本页
    for index, row in df.iterrows():
        word = row['word']
        sentence = row['sentence']

        print(f"\n--- 正在处理单词：'{word}' ---")
        
        # 绘制背景色
        c.setFillColor(BACKGROUND_COLOR)
        c.rect(0, 0, width, height, fill=1)

        img_path = None
        potential_png_path = os.path.join(uploaded_image_dir, f"{index+1}.png")
        potential_jpg_path = os.path.join(uploaded_image_dir, f"{index+1}.jpg")
        
        if os.path.exists(potential_png_path):
            img_path = potential_png_path
        elif os.path.exists(potential_jpg_path):
            img_path = potential_jpg_path
        else:
            print(f"警告：未找到单词 '{word}' 对应的图片文件 (期望: {potential_png_path} 或 {potential_jpg_path})。该页将不显示图片。")
        
        # --- 根据布局样式绘制元素 ---
        if layout_style == 'image_top_text_bottom':
            img_max_width = width * 0.8
            img_max_height = height * 0.4
            img_top_margin = 100
            current_y_position = height - img_top_margin

            if img_path:
                try:
                    img = ImageReader(img_path)
                    img_original_width, img_original_height = img.getSize()
                    aspect_ratio = img_original_width / img_original_height

                    if img_original_width > img_max_width or img_original_height > img_max_height:
                        if (img_max_width / aspect_ratio) <= img_max_height:
                            display_width = img_max_width
                            display_height = img_max_width / aspect_ratio
                        else:
                            display_height = img_max_height
                            display_width = img_max_height * aspect_ratio
                    else:
                        display_width = img_original_width
                        display_height = img_original_height

                    img_x = (width - display_width) / 2
                    img_y = current_y_position - display_height
                    
                    c.drawImage(img, img_x, img_y, display_width, display_height, preserveAspectRatio=True)
                    current_y_position = img_y
                    print(f"图片已绘制 (图片在上，文字在下)。")
                except Exception as e:
                    print(f"绘制图片 '{img_path}' 时发生错误：{e}。该页将不显示图片。")
                    current_y_position = height - img_top_margin - img_max_height
            else:
                current_y_position = height - img_top_margin - 50 # 如果无图，给文字留出上方空间

            text_margin_from_previous_element = 50 

            # 在这里创建 Paragraph 对象，确保它们总是被定义
            word_paragraph = Paragraph(word, word_style)
            sentence_paragraph = Paragraph(sentence, sentence_style)

            w_word, h_word = word_paragraph.wrapOn(c, width * 0.9, height) 
            word_y = current_y_position - text_margin_from_previous_element - h_word
            word_paragraph.drawOn(c, (width - w_word) / 2, word_y)

            w_sentence, h_sentence = sentence_paragraph.wrapOn(c, width * 0.9, height)
            sentence_y = word_y - word_style.spaceAfter - h_sentence
            sentence_paragraph.drawOn(c, (width - w_sentence) / 2, sentence_y)
            print(f"文字已绘制 (图片在上，文字在下)。")

        elif layout_style == 'image_left_text_right':
            # 图片居左，文字居右
            padding = 50 
            middle_gap = 30 
            
            available_horizontal_space = width - 2 * padding - middle_gap
            img_section_width = available_horizontal_space / 2
            text_section_width = available_horizontal_space / 2
            
            # 调整文字样式为左对齐
            word_style_right_aligned = ParagraphStyle('WordStyleRightAligned', parent=word_style, alignment=TA_LEFT)
            sentence_style_right_aligned = ParagraphStyle('SentenceStyleRightAligned', parent=sentence_style, alignment=TA_LEFT)

            # --- 修正：在条件判断之前实例化 Paragraph 对象 ---
            # 这样无论是否有图片，这些对象都会被创建
            temp_word_paragraph = Paragraph(word, word_style_right_aligned)
            temp_sentence_paragraph = Paragraph(sentence, sentence_style_right_aligned)
            # --- 修正结束 ---

            # 计算图片和文字的起始 X 坐标
            img_x_start = padding
            text_x_start = width / 2 + middle_gap / 2 

            available_height = height - 2 * padding 
            
            # 图片部分 (逻辑不变)
            if img_path:
                try:
                    img = ImageReader(img_path)
                    img_original_width, img_original_height = img.getSize()
                    
                    aspect_ratio = img_original_width / img_original_height
                    
                    if img_original_width > img_section_width or img_original_height > available_height:
                        if (img_section_width / aspect_ratio) <= available_height:
                            display_width = img_section_width
                            display_height = img_section_width / aspect_ratio
                        else:
                            display_height = available_height
                            display_width = available_height * aspect_ratio
                    else:
                        display_width = img_original_width
                        display_height = img_original_height

                    img_y = (height - display_height) / 2
                    c.drawImage(img, img_x_start + (img_section_width - display_width) / 2, img_y, display_width, display_height, preserveAspectRatio=True)
                    print(f"图片已绘制 (图片居左，文字居右)。")
                except Exception as e:
                    print(f"绘制图片 '{img_path}' 时发生错误：{e}。该页将不显示图片。")
            else:
                print(f"该页无图片。")

            # 文字部分 (这里使用已经实例化的 temp_word_paragraph 和 temp_sentence_paragraph)
            w_word, h_word = temp_word_paragraph.wrapOn(c, text_section_width, available_height) 
            w_sentence, h_sentence = temp_sentence_paragraph.wrapOn(c, text_section_width, available_height)
            
            total_text_height = h_word + word_style_right_aligned.spaceAfter + h_sentence

            text_block_y_start = (height - total_text_height) / 2
            
            sentence_y = text_block_y_start
            word_y = sentence_y + h_sentence + word_style_right_aligned.spaceAfter

            temp_word_paragraph.drawOn(c, text_x_start, word_y)
            temp_sentence_paragraph.drawOn(c, text_x_start, sentence_y)
            
            print(f"文字已绘制 (图片居左，文字居右)。")

        c.showPage()

    c.save()
    print(f"\n绘本PDF文件已成功生成：{output_pdf_path}")
    return True