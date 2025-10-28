import os
import shutil
import sys
import time
import glob
import re
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                            QHBoxLayout, QPushButton, QLabel, QLineEdit, 
                            QFileDialog, QMessageBox, QTextEdit, QListWidget,
                            QInputDialog, QFrame, QStyledItemDelegate, QSpinBox,
                            QProgressDialog)
from PyQt5.QtCore import Qt, QEvent, QSize, QPoint, QRect
from PyQt5.QtGui import QFont, QMouseEvent, QPainter, QColor, QBrush, QPen, QDrag, QPixmap, QCursor

class DragDropLineEdit(QLineEdit):
    def __init__(self):
        super().__init__()
        self.setAcceptDrops(True)
    
    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
    
    def dropEvent(self, event):
        urls = event.mimeData().urls()
        if urls:
            path = urls[0].toLocalFile()
            if os.path.exists(path):
                # 统一路径格式为Windows格式
                normalized_path = normalize_path(path)
                self.setText(normalized_path)
                # 通知父窗口路径已更改，需要保存
                if hasattr(self.parent(), 'on_path_changed'):
                    self.parent().on_path_changed(self, normalized_path)

# 自定义列表项代理，用于在每个项目前添加数字输入框
class NumberedItemDelegate(QStyledItemDelegate):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent = parent
        
    def paint(self, painter, option, index):
        # 先调用默认绘制
        super().paint(painter, option, index)
        
        # 绘制行号
        rect = option.rect
        row_number = index.row() + 1
        
        # 设置行号区域
        number_rect = QRect(rect.left() + 5, rect.top(), 30, rect.height())
        
        # 绘制行号
        painter.save()
        painter.setPen(QColor("#007AFF"))  # Apple 蓝色
        painter.setFont(QFont("SimSun", 12, QFont.Bold))
        painter.drawText(number_rect, Qt.AlignCenter, str(row_number))
        painter.restore()
        
    def createEditor(self, parent, option, index):
        editor = QSpinBox(parent)
        editor.setMinimum(1)
        editor.setMaximum(999)
        editor.setFrame(False)
        editor.setFixedWidth(50)
        # 当编辑完成时关闭编辑器
        editor.editingFinished.connect(lambda: self.commitAndCloseEditor(editor))
        return editor
        
    def commitAndCloseEditor(self, editor):
        # 提交数据并关闭编辑器
        self.commitData.emit(editor)
        self.closeEditor.emit(editor, QStyledItemDelegate.NoHint)
        
        # 清除列表中的当前编辑器引用
        if self.parent and hasattr(self.parent, 'current_editor_item'):
            self.parent.current_editor_item = None
        
    def setEditorData(self, editor, index):
        value = index.row() + 1
        editor.setValue(value)
        
    def setModelData(self, editor, model, index):
        value = editor.value()
        # 获取当前项的文本
        current_text = model.data(index, Qt.DisplayRole)
        # 获取当前行
        current_row = index.row()
        
        # 通知父窗口处理排序
        if self.parent and hasattr(self.parent, 'reorderItem'):
            self.parent.reorderItem(current_row, value - 1)
            
    def updateEditorGeometry(self, editor, option, index):
        editor.setGeometry(option.rect.x() + 5, option.rect.y(), 
                          50, option.rect.height())

# 修改 DraggableListWidget 类，添加数字排序功能
class NumberedListWidget(QListWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setDragDropMode(QListWidget.InternalMove)
        self.setDefaultDropAction(Qt.MoveAction)
        self.setSelectionMode(QListWidget.MultiSelection)
        self.setAcceptDrops(True)
        self.setDragEnabled(True)
        self.setDragDropOverwriteMode(False)
        self.setFocusPolicy(Qt.NoFocus)
        
        # 设置自定义代理
        self.delegate = NumberedItemDelegate(self)
        self.setItemDelegate(self.delegate)
        
        # 设置样式，为行号留出空间
        self.setStyleSheet("""
            QListWidget {
                border: 1px solid #E5E5EA;
                border-radius: 10px;
                background-color: white;
                padding: 10px;
                font-family: SimSun;
                font-size: 14pt;
            }
            QListWidget::item {
                height: 35px;
                padding-left: 40px;  /* 为行号留出空间 */
                border-radius: 5px;
                border: 1px solid transparent;
                margin: 2px 0px;
                background-color: #F7F7F7;
            }
            QListWidget::item:hover:!selected {
                background-color: #E5E5EA;
            }
            QListWidget::item:selected {
                background-color: #007AFF;
                color: white;
                border: 1px solid #007AFF;
            }
        """)
        
        # 跟踪当前打开的编辑器
        self.current_editor_item = None
        
        # 修改双击事件处理
        self.itemDoubleClicked.connect(self.onItemDoubleClicked)
        
    def onItemDoubleClicked(self, item):
        # 检查点击位置是否在行号区域
        pos = self.mapFromGlobal(QCursor.pos())
        item_rect = self.visualItemRect(item)
        
        # 如果点击在行号区域（左侧40像素）
        if pos.x() < item_rect.left() + 40:
            # 如果有其他编辑器打开，先关闭它
            if self.current_editor_item and self.current_editor_item != item:
                self.closePersistentEditor(self.current_editor_item)
                
            # 打开编辑器
            self.openPersistentEditor(item)
            self.current_editor_item = item
        else:
            # 否则切换选中状态
            item.setSelected(not item.isSelected())
            
            # 如果有打开的编辑器，关闭它
            if self.current_editor_item:
                self.closePersistentEditor(self.current_editor_item)
                self.current_editor_item = None
        
    def reorderItem(self, from_row, to_row):
        # 确保行号有效
        if from_row == to_row or from_row < 0 or to_row < 0 or from_row >= self.count() or to_row >= self.count():
            return
            
        # 取出项目
        item = self.takeItem(from_row)
        
        # 插入到新位置
        self.insertItem(to_row, item)
        
        # 关闭编辑器
        self.closePersistentEditor(item)
        
        # 选中移动后的项目
        self.setCurrentItem(item)
        
        # 保存更新后的顺序
        if isinstance(self.parent(), ImageSortingApp):
            self.parent().save_card_types()
            
    def dropEvent(self, event):
        # 记住选中的项目
        selected_items = self.selectedItems()
        
        # 调用父类处理放置
        super().dropEvent(event)
        
        # 保存更新后的顺序
        if event.isAccepted() and isinstance(self.parent(), ImageSortingApp):
            self.parent().save_card_types()
            
        # 恢复选中状态
        for item in selected_items:
            item.setSelected(True)

def normalize_path(path):
    """将路径统一为Windows格式的独立函数"""
    if not path:
        return path
    
    # 将正斜杠替换为反斜杠
    normalized = path.replace('/', '\\')
    
    # 处理os.path.join生成的路径，确保使用Windows分隔符
    # os.path.join在Windows上会使用反斜杠，但为了确保一致性，我们再次标准化
    normalized = normalized.replace('/', '\\')
    
    # 确保路径以正确的驱动器格式开始
    if normalized.startswith('\\'):
        # 如果是网络路径，保持原样
        pass
    elif ':' not in normalized[:2]:
        # 如果没有驱动器标识符，添加当前驱动器
        import os
        current_drive = os.getcwd()[:2]  # 获取当前驱动器，如 "C:"
        normalized = current_drive + '\\' + normalized.lstrip('\\')
    
    return normalized

class ImageSortingApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setFixedSize(1600, 900)
        self.setWindowTitle('照片分类工具')
        
        # 设置全局字体
        font = QFont("SimSun", 14)
        QApplication.setFont(font)
        
        # 初始化证件类型列表
        self.default_card_types = [
            "身份证正面", "身份证背面", "学历-中专", "学历-大专", "学历-本科",
            "保安员证", "退伍证", "消防设施操作员", "本科证", "学士学位证",
            "三级保安员证", "驾驶证", "建筑物消防员", "计算机操作员",
            "安检培训合格证正面", "安检培训合格证背面", "计算机调试员四级1",
            "计算机调试员四级2", "助理工程师1", "助理工程师2", "保安员证", "护照"
        ]
        
        # 初始化默认命名格式列表
        self.default_formats = [
            "图片 {n}",
            "图片-{n}",
            "IMG_{n}",
            "{n}号照片",
            "photo_{n}",
            "image_{n}"
        ]
        
        # 初始化历史记录相关属性
        self.history_stack = []
        self.max_history = 50  # 最大历史记录数
        
        # 获取程序所在目录 - 兼容exe环境
        if getattr(sys, 'frozen', False):
            # 如果是exe环境，使用sys.executable
            self.app_dir = os.path.dirname(sys.executable)
        else:
            # 如果是Python环境，使用__file__
            self.app_dir = os.path.dirname(os.path.abspath(__file__))
        
        # 设置文件路径
        self.data_dir = normalize_path(os.path.join(self.app_dir, "data"))
        self.card_types_file = normalize_path(os.path.join(self.data_dir, "card.txt"))
        self.dest_path_file = normalize_path(os.path.join(self.data_dir, "path.txt"))
        self.name_format_file = normalize_path(os.path.join(self.data_dir, "name.txt"))
        self.default_name_format_file = normalize_path(os.path.join(self.data_dir, "name_default.txt"))
        
        # 确保data目录存在并初始化所有必要文件
        try:
            print(f"程序目录: {self.app_dir}")
            print(f"数据目录: {self.data_dir}")
            
            # 强制创建data目录
            if not os.path.exists(self.data_dir):
                os.makedirs(self.data_dir, exist_ok=True)
                print(f'创建data目录: {self.data_dir}')
            else:
                print(f'data目录已存在: {self.data_dir}')
            
            # 只在文件不存在时创建默认配置文件
            print("检查配置文件...")
            
            # 证件类型文件
            if not os.path.exists(self.card_types_file):
                try:
                    with open(self.card_types_file, 'w', encoding='utf-8') as f:
                        f.write('\n'.join(self.default_card_types))
                    print(f'已创建证件类型文件: {self.card_types_file}')
                except Exception as e:
                    print(f'创建证件类型文件失败: {e}')
                    import traceback
                    traceback.print_exc()
            else:
                print(f'证件类型文件已存在: {self.card_types_file}')
            
            # 目标路径文件
            if not os.path.exists(self.dest_path_file):
                try:
                    desktop_path = normalize_path(os.path.join(os.path.expanduser("~"), "Desktop"))
                    if not os.path.exists(desktop_path):
                        desktop_path = normalize_path(os.path.join(os.path.expanduser("~"), "桌面"))
                    if not os.path.exists(desktop_path):
                        desktop_path = "C:\\Users\\Public\\Desktop"
                    
                    # 统一路径格式为Windows格式
                    normalized_desktop_path = normalize_path(desktop_path)
                    
                    with open(self.dest_path_file, 'w', encoding='utf-8') as f:
                        f.write(normalized_desktop_path)
                    print(f'已创建目标路径文件: {self.dest_path_file}')
                except Exception as e:
                    print(f'创建目标路径文件失败: {e}')
                    import traceback
                    traceback.print_exc()
            else:
                print(f'目标路径文件已存在: {self.dest_path_file}')
            
            # 命名格式文件
            if not os.path.exists(self.name_format_file):
                try:
                    with open(self.name_format_file, 'w', encoding='utf-8') as f:
                        f.write('\r\n'.join(self.default_formats))
                    print(f'已创建命名格式文件: {self.name_format_file}')
                except Exception as e:
                    print(f'创建命名格式文件失败: {e}')
                    import traceback
                    traceback.print_exc()
            else:
                print(f'命名格式文件已存在: {self.name_format_file}')

            # 默认命名格式文件
            if not os.path.exists(self.default_name_format_file):
                try:
                    with open(self.default_name_format_file, 'w', encoding='utf-8') as f:
                        f.write('图片 {n}')
                    print(f'已创建默认命名格式文件: {self.default_name_format_file}')
                except Exception as e:
                    print(f'创建默认命名格式文件失败: {e}')
                    import traceback
                    traceback.print_exc()
            else:
                print(f'默认命名格式文件已存在: {self.default_name_format_file}')
            
            # 验证文件创建
            if all([
                os.path.exists(self.card_types_file),
                os.path.exists(self.dest_path_file),
                os.path.exists(self.name_format_file),
                os.path.exists(self.default_name_format_file)
            ]):
                print("所有配置文件创建成功！")
            else:
                print("部分配置文件创建失败")
                
        except Exception as e:
            print(f'初始化配置目录失败：{str(e)}')
            import traceback
            traceback.print_exc()
            # 不退出程序，继续运行
        
        # 初始化界面
        self.initUI()
        
        # 加载保存的路径、证件类型和命名格式
        self.load_dest_path()
        self.load_card_types()  # 加回证件类型列表的加载
        self.load_naming_formats()
        self.load_default_naming_format()
        

        


    def load_card_types(self):
        """加载证件类型列表"""
        try:
            if os.path.exists(self.card_types_file):
                with open(self.card_types_file, 'r', encoding='utf-8') as f:
                    card_types = [line.strip() for line in f.readlines() if line.strip()]
                self.card_types_list.clear()  # 清除现有项目
                self.card_types_list.addItems(card_types)
                # 初始化历史记录
                self.history_stack = [card_types.copy()]
                return
        except Exception as e:
            print(f"加载证件类型失败: {str(e)}")
            QMessageBox.warning(self, '警告', f'加载证件类型文件失败：{str(e)}')
        
        # 如果文件不存在或加载失败，使用默认类型
        self.card_types_list.clear()
        self.card_types_list.addItems(self.default_card_types)
        # 初始化历史记录
        self.history_stack = [self.default_card_types.copy()]

    def save_card_types(self):
        """保存证件类型列表"""
        try:
            card_types = [self.card_types_list.item(i).text() 
                         for i in range(self.card_types_list.count())]
            
            # 保存当前状态到历史记录栈（只有在状态变化时才保存）
            if not self.history_stack or card_types != self.history_stack[-1]:
                # 深拷贝当前状态
                self.history_stack.append(card_types.copy())
                print(f'保存历史记录，当前历史记录数: {len(self.history_stack)}')
                
                # 如果历史记录超过最大值，删除最早的记录
                if len(self.history_stack) > self.max_history:
                    self.history_stack.pop(0)
            
            # 使用 UTF-8 编码保存，确保没有 BOM 标记，使用 Windows 换行符
            with open(self.card_types_file, 'w', encoding='utf-8') as f:
                f.write('\n'.join(card_types))
                
            print(f'证件类型列表已保存到 {self.card_types_file}')
        except Exception as e:
            print(f"保存证件类型失败: {str(e)}")
            QMessageBox.warning(self, '警告', f'保存证件类型文件失败：{str(e)}')

    def initUI(self):
        """初始化界面"""
        # 创建中央部件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # 初始化所有控件
        self.source_edit = DragDropLineEdit()
        self.dest_edit = DragDropLineEdit()
        self.id_numbers_edit = QTextEdit()
        self.card_types_list = NumberedListWidget(self)
        self.card_type_edit = QLineEdit()
        self.search_edit = QLineEdit()
        self.naming_format_edit = QLineEdit()
        self.naming_list = QListWidget()
        
        # 创建主布局
        main_layout = QHBoxLayout(central_widget)
        main_layout.setSpacing(20)
        main_layout.setContentsMargins(20, 20, 20, 20)
        
        # 左侧布局 - 证件类型列表
        left_widget = QWidget()
        left_widget.setFixedWidth(400)
        left_layout = QVBoxLayout(left_widget)
        left_layout.setSpacing(10)
        left_layout.setContentsMargins(0, 0, 0, 0)
        
        # 按钮区域
        buttons_layout = QHBoxLayout()
        buttons_layout.setSpacing(8)
        
        # 定义按钮及其样式 - Apple 风格
        buttons = [
            ("全选", self.select_all_items, "#007AFF", "#0062CC", "#004999"),    # Apple 蓝
            ("取消", self.deselect_all_items, "#007AFF", "#0062CC", "#004999"),  # Apple 蓝
            ("新增", self.show_add_dialog, "#007AFF", "#0062CC", "#004999"),     # Apple 蓝
            ("删除", self.delete_selected_items, "#FF3B30", "#CC2F26", "#991F1C") # Apple 红
        ]
        
        for btn_text, btn_slot, normal_color, hover_color, pressed_color in buttons:
            btn = QPushButton(btn_text)
            btn.setFixedWidth(65)
            btn.setFixedHeight(35)
            btn.setStyleSheet(f"""
                QPushButton {{
                    border-radius: 6px;
                    padding: 5px 10px;
                    background-color: {normal_color};
                    color: white;
                    border: none;
                    font-family: SimSun;
                    font-size: 14pt;
                }}
                QPushButton:hover {{
                    background-color: {hover_color};
                }}
                QPushButton:pressed {{
                    background-color: {pressed_color};
                }}
            """)
            btn.clicked.connect(btn_slot)
            buttons_layout.addWidget(btn)
        
        left_layout.addLayout(buttons_layout)
        
        # 证件类型标题
        card_types_label = QLabel("证件类型列表")
        card_types_label.setStyleSheet("""
            QLabel {
                font-family: SimSun;
                font-size: 14pt;
                color: #333333;
                padding-left: 5px;
            }
        """)
        left_layout.addWidget(card_types_label)
        
        # 添加搜索框
        self.search_edit.setPlaceholderText("搜索证件类型...")
        self.search_edit.setStyleSheet("""
            QLineEdit {
                border: 1px solid #E5E5EA;
                border-radius: 15px;
                padding: 5px 10px;
                background-color: white;
                font-family: SimSun;
                font-size: 12pt;
                margin: 5px 0px;
            }
            QLineEdit:focus {
                border: 2px solid #007AFF;
            }
        """)
        self.search_edit.textChanged.connect(self.filter_card_types)
        left_layout.addWidget(self.search_edit)
        
        # 证件类型列表
        self.card_types_list.setStyleSheet("""
            QListWidget {
                border: 1px solid #E5E5EA;
                border-radius: 10px;
                background-color: white;
                padding: 10px;
                font-family: SimSun;
                font-size: 14pt;
                margin-top: 5px;
            }
            QListWidget::item {
                height: 35px;
                padding-left: 40px;
                border-radius: 5px;
                border: 1px solid transparent;
                margin: 2px 0px;
                background-color: #F7F7F7;
            }
            QListWidget::item:hover:!selected {
                background-color: #E5E5EA;
            }
            QListWidget::item:selected {
                background-color: #007AFF;
                color: white;
                border: 1px solid #007AFF;
            }
        """)
        left_layout.addWidget(self.card_types_list)
        
        # 添加左右布局到主布局
        main_layout.addWidget(left_widget)
        
        # 中间布局 - 原有的右侧内容
        middle_widget = QWidget()
        middle_layout = QVBoxLayout(middle_widget)
        middle_layout.setSpacing(15)
        
        # 添加一个空白占位区域
        spacer = QWidget()
        spacer.setFixedHeight(85)
        middle_layout.addWidget(spacer)
        
        # 原有的右侧内容移到中间
        self.add_input_section(middle_layout, "源文件夹:", self.source_edit, "选择源文件夹")
        self.add_input_section(middle_layout, "目标文件夹:", self.dest_edit, "选择目标文件夹")
        
        # 监听目标文件夹输入框的文本变化，自动保存路径
        # 延迟连接，避免程序启动时触发
        from PyQt5.QtCore import QTimer
        QTimer.singleShot(100, lambda: self.dest_edit.textChanged.connect(self.on_dest_path_text_changed))
        
        # 姓名+身份证号输入区域
        id_numbers_label = QLabel("请输入姓名+身份证号（每行一个）:")
        id_numbers_label.setStyleSheet("""
            QLabel {
                font-family: SimSun;
                font-size: 14pt;
                color: #333333;
                padding-left: 5px;
            }
        """)
        middle_layout.addWidget(id_numbers_label)
        
        # 设置姓名+身份证号输入框的样式和占位符
        self.id_numbers_edit.setPlaceholderText("请输入姓名+身份证号，每行一个\n例如：\n李四+110101199001011234\n（程序会自动添加-证件类型和扩展名）")
        self.id_numbers_edit.setStyleSheet("""
            QTextEdit {
                border: 1px solid #E5E5EA;
                border-radius: 10px;
                padding: 10px;
                background-color: white;
                font-family: SimSun;
                font-size: 14pt;
                min-height: 120px;
            }
            QTextEdit:focus {
                border: 2px solid #007AFF;
            }
        """)
        middle_layout.addWidget(self.id_numbers_edit)
        
        # 导出日志按钮
        export_log_btn = QPushButton("导出日志")
        export_log_btn.setFixedSize(180, 40)
        export_log_btn.setStyleSheet("""
            QPushButton {
                border-radius: 20px;
                padding: 5px 15px;
                background-color: #F2F2F7;
                color: #007AFF;
                border: 1px solid #E5E5EA;
                font-family: SimSun;
                font-size: 14pt;  /* 宋体四号 */
                font-weight: normal;
            }
            QPushButton:hover {
                background-color: #E5E5EA;
                color: #0062CC;
            }
            QPushButton:pressed {
                background-color: #D1D1D6;
                color: #004999;
            }
        """)
        export_log_btn.clicked.connect(self.export_log)
        
        # 添加导出日志按钮到布局
        export_btn_layout = QHBoxLayout()
        export_btn_layout.addStretch()
        export_btn_layout.addWidget(export_log_btn)
        middle_layout.addLayout(export_btn_layout)

        # 日志区域
        self.log_text = QTextEdit()
        middle_layout.addWidget(self.log_text)
        
        # 开始处理按钮
        start_btn = QPushButton("开始处理")
        start_btn.setFixedSize(180, 40)
        start_btn.setStyleSheet("""
            QPushButton {
                border-radius: 20px;
                background-color: #007AFF;
                color: white;
                border: none;
                font-family: SimSun;
                font-size: 14pt;  /* 宋体四号 */
                font-weight: normal;
            }
            QPushButton:hover {
                background-color: #0062CC;
            }
            QPushButton:pressed {
                background-color: #004999;
            }
        """)
        start_btn.clicked.connect(self.process_files)
        
        # 添加开始处理按钮到布局（居中）
        middle_layout.addWidget(start_btn, alignment=Qt.AlignCenter)
        
        main_layout.addWidget(middle_widget)
        
        # 右侧布局 - 命名格式
        right_widget = QWidget()
        right_widget.setFixedWidth(400)
        right_layout = QVBoxLayout(right_widget)
        right_layout.setSpacing(10)
        right_layout.setContentsMargins(0, 0, 0, 0)

        # 按钮区域
        format_buttons_layout = QHBoxLayout()
        format_buttons_layout.setSpacing(8)
        format_buttons = [
            ("新增", self.add_naming_format, "#007AFF", "#0062CC", "#004999"),
            ("删除", self.delete_naming_format, "#FF3B30", "#CC2F26", "#991F1C"),
            ("设为默认", self.set_default_naming_format, "#34C759", "#28A745", "#1E7E34")
        ]
        
        for btn_text, btn_slot, normal_color, hover_color, pressed_color in format_buttons:
            btn = QPushButton(btn_text)
            # 让“设为默认”按钮宽一些，避免文字被截断
            if btn_text == "设为默认":
                btn.setFixedWidth(100)
            else:
                btn.setFixedWidth(65)
            btn.setFixedHeight(35)
            btn.setStyleSheet(f"""
                QPushButton {{
                    border-radius: 6px;
                    padding: 5px 10px;
                    background-color: {normal_color};
                    color: white;
                    border: none;
                    font-family: SimSun;
                    font-size: 14pt;
                }}
                QPushButton:hover {{
                    background-color: {hover_color};
                }}
                QPushButton:pressed {{
                    background-color: {pressed_color};
                }}
            """)
            btn.clicked.connect(btn_slot)
            format_buttons_layout.addWidget(btn)
        
        format_buttons_layout.addStretch()
        right_layout.addLayout(format_buttons_layout)

        # 添加标题
        right_title = QLabel("图片命名格式")
        right_title.setStyleSheet("""
            QLabel {
                font-family: SimSun;
                font-size: 14pt;
                color: #333333;
                padding-left: 5px;
            }
        """)
        right_layout.addWidget(right_title)

        # 添加搜索框
        self.format_search = QLineEdit()
        self.format_search.setPlaceholderText("搜索命名格式...")
        self.format_search.setStyleSheet("""
            QLineEdit {
                border: 1px solid #E5E5EA;
                border-radius: 15px;
                padding: 5px 10px;
                background-color: white;
                font-family: SimSun;
                font-size: 12pt;
                margin: 5px 0px;
            }
            QLineEdit:focus {
                border: 2px solid #007AFF;
            }
        """)
        self.format_search.textChanged.connect(self.filter_formats)
        right_layout.addWidget(self.format_search)

        # 添加命名格式输入框
        self.naming_format_edit.setText("图片 {n}")  # 默认格式（启动后会被默认值覆盖）
        self.naming_format_edit.setPlaceholderText("例如: 图片 {n}")
        self.naming_format_edit.setStyleSheet("""
            QLineEdit {
                border: 1px solid #E5E5EA;
                border-radius: 6px;
                padding: 5px 10px;
                background-color: white;
                font-family: SimSun;
                font-size: 14pt;
                min-height: 35px;
                margin: 5px 0px;
            }
            QLineEdit:focus {
                border: 2px solid #007AFF;
            }
        """)
        right_layout.addWidget(self.naming_format_edit)

        # 添加格式说明标签
        format_hint = QLabel("自定义图片命名规则")
        format_hint.setStyleSheet("""
            QLabel {
                font-family: SimSun;
                font-size: 12pt;
                color: #666666;
                padding-left: 5px;
            }
        """)
        right_layout.addWidget(format_hint)

        # 添加命名格式列表
        self.naming_list.addItems([
            "图片 {n}",
            "图片-{n}",
            "IMG_{n}",
            "{n}号照片",
            "photo_{n}",
            "image_{n}"
        ])
        
        self.naming_list.setStyleSheet("""
            QListWidget {
                border: 1px solid #E5E5EA;
                border-radius: 10px;
                background-color: white;
                padding: 10px;
                font-family: SimSun;
                font-size: 14pt;
                margin-top: 5px;
            }
            QListWidget::item {
                height: 35px;
                padding-left: 10px;
                border-radius: 5px;
                border: 1px solid transparent;
                margin: 2px 0px;
                background-color: #F7F7F7;
            }
            QListWidget::item:hover:!selected {
                background-color: #E5E5EA;
            }
            QListWidget::item:selected {
                background-color: #007AFF;
                color: white;
                border: 1px solid #007AFF;
            }
        """)
        
        # 连接命名格式列表的信号
        self.naming_list.itemSelectionChanged.connect(self.on_format_selection_changed)
        self.naming_list.itemDoubleClicked.connect(self.on_format_double_clicked)
        right_layout.addWidget(self.naming_list)
        
        # 添加到主布局
        main_layout.addWidget(right_widget)
        
        # 设置主布局
        central_widget.setLayout(main_layout)

    def add_input_section(self, parent_layout, label_text, line_edit, button_text):
        layout = QHBoxLayout()
        layout.setSpacing(20)
        
        # 标签
        label = QLabel(label_text)
        label.setFixedWidth(150)
        label.setStyleSheet("""
            QLabel {
                font-family: SimSun;
                font-size: 14pt;
                color: #333333;
                padding-left: 5px;
            }
        """)
        layout.addWidget(label)
        
        # 输入框 - Apple 风格
        line_edit.setFixedHeight(40)
        line_edit.setMinimumWidth(500)
        if "目标文件夹" in label_text:
            line_edit.setPlaceholderText("默认使用自动创建的输出目录")
        else:
            line_edit.setPlaceholderText("拖拽或点击按钮选择")
        line_edit.setStyleSheet("""
            QLineEdit {
                border-radius: 10px;
                border: 1px solid #E5E5EA;
                padding: 5px 10px;
                background-color: white;
                font-family: SimSun;
                font-size: 14pt;
            }
            QLineEdit:hover {
                border: 1px solid #007AFF;
            }
            QLineEdit:focus {
                border: 2px solid #007AFF;
                background-color: #FFFFFF;
            }
            QLineEdit[placeholderText] {
                color: #8E8E93;
            }
        """)
        layout.addWidget(line_edit)
        
        # 浏览按钮 - Apple 风格
        browse_btn = QPushButton(button_text)
        browse_btn.setFixedWidth(180)
        browse_btn.setFixedHeight(40)
        browse_btn.setStyleSheet("""
            QPushButton {
                border-radius: 10px;
                padding: 5px 15px;
                background-color: #F2F2F7;
                color: #007AFF;
                border: 1px solid #E5E5EA;
                font-family: SimSun;
                font-size: 14pt;
            }
            QPushButton:hover {
                background-color: #E5E5EA;
                color: #0062CC;
            }
            QPushButton:pressed {
                background-color: #D1D1D6;
                color: #004999;
            }
        """)
        browse_btn.clicked.connect(lambda: self.browse_path(line_edit, '文件夹' in button_text))
        layout.addWidget(browse_btn)
        
        parent_layout.addLayout(layout)
        
    def browse_path(self, line_edit, is_folder=True):
        print(f"browse_path 被调用，line_edit: {line_edit}")
        
        if is_folder:
            path = QFileDialog.getExistingDirectory(self, '选择文件夹')
        else:
            path, _ = QFileDialog.getOpenFileName(self, '选择文件', '', 'Text Files (*.txt)')
        if path:
            # 统一路径格式为Windows格式
            normalized_path = self.normalize_path(path)
            line_edit.setText(normalized_path)
            print(f"选择的路径: {normalized_path}")
            
            # 通过检查占位符文本来判断是否是目标文件夹输入框
            if line_edit.placeholderText() == "默认使用自动创建的输出目录":
                self.save_dest_path(normalized_path)
                print(f"目标文件夹已选择并保存: {normalized_path}")
            else:
                print("不是目标文件夹输入框，不保存路径")
            
    def log(self, message):
        self.log_text.append(message)
        
    def process_files(self):
        """处理文件"""
        try:
            src_dir = self.normalize_path(self.source_edit.text())
            base_dst_dir = self.normalize_path(self.dest_edit.text())
            
            if not src_dir or not base_dst_dir:
                self.show_message('警告', '请选择源文件夹和目标文件夹')
                return
                
            if not os.path.exists(src_dir):
                self.show_message('警告', '源文件夹不存在')
                return
                
            if not os.path.exists(base_dst_dir):
                self.show_message('警告', '目标文件夹不存在')
                return
                
            # 创建输出目录
            output_dir = self.normalize_path(os.path.join(base_dst_dir, "输出目录"))
            if os.path.exists(output_dir):
                # 如果输出目录已存在，尝试创建输出目录1、输出目录2等
                i = 1
                while os.path.exists(output_dir):
                    output_dir = self.normalize_path(os.path.join(base_dst_dir, f"输出目录{i}"))
                    i += 1
            
            # 创建输出目录
            os.makedirs(output_dir, exist_ok=True)
            
            # 获取选中的证件类型
            selected_card_types = [item.text() for item in self.card_types_list.selectedItems()]
            if not selected_card_types:
                self.show_message('警告', '请选择至少一种证件类型')
                return
            
            # 获取姓名+身份证号列表
            name_id_pairs = [line.strip() for line in self.id_numbers_edit.toPlainText().split('\n') if line.strip()]
            
            if not name_id_pairs:
                self.show_message('警告', '请输入至少一个姓名+身份证号')
                return
            
            # 获取文件列表并排序
            files = self.get_sorted_files(src_dir)
            if not files:
                self.show_message('警告', '源文件夹中没有符合命名格式的图片文件')
                return
            
            # 验证输入格式
            for i, line in enumerate(name_id_pairs):
                if not self.is_valid_name_id_format(line):
                    self.show_message('警告', f'第{i+1}行格式不正确：{line}\n正确格式：姓名+身份证号，例如：李四+110101199001011234')
                    return
            
            # 计算总数并验证
            images_per_person = len(selected_card_types)
            total_images_needed = len(name_id_pairs) * images_per_person
            
            if len(files) != total_images_needed:
                self.show_message('警告', 
                    f'图片数量不匹配！\n'
                    f'每个人需要 {images_per_person} 张图片\n'
                    f'共有 {len(name_id_pairs)} 个人\n'
                    f'需要的总图片数：{total_images_needed}\n'
                    f'实际图片数量：{len(files)}')
                return
            
            # 显示进度对话框
            progress = QProgressDialog("正在处理文件...", "取消", 0, total_images_needed, self)
            progress.setWindowModality(Qt.WindowModal)
            progress.setMinimumDuration(0)
            processed_count = 0
            
            # 按姓名+身份证号分组处理文件
            for i, name_id_pair in enumerate(name_id_pairs):
                if progress.wasCanceled():
                    break
                
                try:
                    # 在输出目录下创建每个姓名+身份证号的目录
                    person_dir = self.normalize_path(os.path.join(output_dir, name_id_pair))
                    os.makedirs(person_dir, exist_ok=True)
                    
                    # 获取这个人的图片
                    start_idx = i * images_per_person
                    person_files = files[start_idx:start_idx + images_per_person]
                    
                    # 复制并重命名文件
                    for src_file, card_type in zip(person_files, selected_card_types):
                        if progress.wasCanceled():
                            break
                        
                        try:
                            # 生成目标文件名：姓名+身份证号-证件类型
                            new_name = f"{name_id_pair}-{card_type}{os.path.splitext(src_file)[1]}"
                            dst_file = self.normalize_path(os.path.join(person_dir, new_name))
                            
                            # 复制文件
                            shutil.copy2(src_file, dst_file)
                            self.log(f'已复制到 {name_id_pair} 的文件夹: {os.path.basename(src_file)} -> {new_name}')
                            
                            processed_count += 1
                            progress.setValue(processed_count)
                            QApplication.processEvents()
                            
                        except Exception as e:
                            self.log(f'处理文件出错 {src_file}: {str(e)}')
                            continue
                            
                except Exception as e:
                    self.log(f'处理 {name_id_pair} 的文件夹时出错: {str(e)}')
                    continue
            
            if processed_count == total_images_needed:
                self.show_message(
                    '完成', 
                    f'文件处理完成！\n'
                    f'已处理 {len(name_id_pairs)} 个姓名+身份证号文件夹\n'
                    f'共处理 {processed_count} 个文件'
                )
                
        except Exception as e:
            self.show_message('错误', f'处理文件时出错：{str(e)}')
        finally:
            if 'progress' in locals():
                progress.close()

    def clear_all_items(self):
        """清空所有项目"""
        reply = self.show_message(
            '确认清空',
            '确定要清空所有证件类型吗？',
            QMessageBox.Question,
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            self.card_types_list.clear()
            self.save_card_types()

    def select_all_items(self):
        """全选/取消全选切换"""
        # 检查是否所有项目都被选中
        all_selected = all(self.card_types_list.item(i).isSelected() 
                          for i in range(self.card_types_list.count()))
        
        # 如果全部选中，则取消全选；否则全选
        for i in range(self.card_types_list.count()):
            self.card_types_list.item(i).setSelected(not all_selected)

    def show_add_dialog(self):
        """显示新增对话框"""
        text, ok = QInputDialog.getText(self, '新增证件类型', 
                                      '请输入新的证件类型名称:', 
                                      QLineEdit.Normal)
        if ok and text.strip():
            # 获取当前选中的项目
            current_row = self.card_types_list.currentRow()
            
            # 如果有选中项，则在其后插入；否则添加到末尾
            if current_row >= 0:
                self.card_types_list.insertItem(current_row + 1, text.strip())
                self.card_types_list.setCurrentRow(current_row + 1)  # 选中新插入的项
            else:
                self.card_types_list.addItem(text.strip())
                self.card_types_list.setCurrentRow(self.card_types_list.count() - 1)  # 选中新添加的项
            
            self.save_card_types()

    def delete_selected_items(self):
        """删除选中的项目"""
        selected_items = self.card_types_list.selectedItems()
        if not selected_items:
            self.show_message('警告', '请先选择要删除的项目', QMessageBox.Warning)
            return
        
        reply = self.show_message(
            '确认删除',
            f'确定要删除选中的 {len(selected_items)} 个项目吗？',
            QMessageBox.Question,
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            for item in selected_items:
                self.card_types_list.takeItem(self.card_types_list.row(item))
            self.save_card_types()

    def export_log(self):
        """导出日志到文件"""
        try:
            # 获取当前时间作为文件名
            current_time = time.strftime("%Y%m%d_%H%M%S")
            default_filename = f"日志记录_{current_time}.txt"
            
            # 打开文件保存对话框
            filename, _ = QFileDialog.getSaveFileName(
                self,
                "导出日志",
                default_filename,
                "Text Files (*.txt);;All Files (*)"
            )
            
            if filename:
                # 如果用户没有指定.txt后缀，自动添加
                if not filename.endswith('.txt'):
                    filename += '.txt'
                    
                # 将日志内容写入文件，使用正确的编码和换行符
                with open(filename, 'w', encoding='utf-8') as f:
                    f.write(self.log_text.toPlainText())
                
                self.show_message("成功", "日志导出成功！")
                
        except Exception as e:
            self.show_message("错误", f"导出日志时出错：{str(e)}", QMessageBox.Critical)





    def on_item_clicked(self, item):
        """处理列表项的点击事件"""
        # 不需要手动切换选中状态，让 QListWidget 自己处理
        pass

    def on_item_moved(self):
        """当列表项被拖拽移动后保存更新"""
        self.save_card_types()

    def closeEvent(self, event):
        """程序关闭时的事件处理"""
        # 保存当前证件类型列表
        self.save_card_types()
        event.accept()

    def filter_card_types(self, text):
        """根据搜索文本过滤证件类型列表"""
        # 遍历所有项目
        for i in range(self.card_types_list.count()):
            item = self.card_types_list.item(i)
            # 如果搜索文本为空或者文本匹配，则显示项目
            if not text or text.lower() in item.text().lower():
                item.setHidden(False)
            else:
                item.setHidden(True)
                # 如果项目被隐藏，取消其选中状态
                if item.isSelected():
                    item.setSelected(False)

    def deselect_all_items(self):
        """取消全选"""
        for i in range(self.card_types_list.count()):
            self.card_types_list.item(i).setSelected(False)

    def show_naming_help(self):
        """显示命名格式帮助信息"""
        help_text = """命名格式说明：
        
1. 使用 {n} 表示序号位置
2. 序号会自动从1开始递增
3. 示例：
   - 图片 {n}    →  图片 1.png, 图片 2.png
   - 图片-{n}    →  图片-1.png, 图片-2.png
   - IMG_{n}     →  IMG_1.png, IMG_2.png
   - {n}号照片   →  1号照片.png, 2号照片.png"""
        
        msg = QMessageBox(self)
        msg.setWindowTitle('命名格式说明')
        msg.setText(help_text)
        msg.setStyleSheet("""
            QMessageBox {
                background-color: white;
            }
            QLabel {
                font-family: SimSun;
                font-size: 14pt;
                color: #333333;
                min-width: 400px;
            }
            QPushButton {
                border-radius: 6px;
                padding: 5px 20px;
                background-color: #007AFF;
                color: white;
                border: none;
                font-family: SimSun;
                font-size: 14pt;
                min-width: 80px;
                min-height: 35px;
                margin: 10px;
            }
            QPushButton:hover {
                background-color: #0062CC;
            }
            QPushButton:pressed {
                background-color: #004999;
            }
        """)
        msg.exec_()

    def on_format_selection_changed(self):
        """当选择的命名格式改变时更新输入框"""
        if self.naming_list.selectedItems():
            selected_format = self.naming_list.selectedItems()[0].text()
            self.naming_format_edit.setText(selected_format)

    def on_format_double_clicked(self, item):
        """双击取消选择"""
        self.naming_list.clearSelection()
        # 恢复为系统默认格式
        self.naming_format_edit.setText(self.get_default_naming_format())

    def load_naming_formats(self):
        """从文件加载命名格式列表"""
        try:
            if os.path.exists(self.name_format_file):
                with open(self.name_format_file, 'r', encoding='utf-8') as f:
                    formats = [line.strip() for line in f.readlines() if line.strip()]
                self.naming_list.clear()
                self.naming_list.addItems(formats)
        except Exception as e:
            print(f"加载命名格式失败: {e}")

    def save_naming_formats(self):
        """保存命名格式列表到文件"""
        try:
            formats = [self.naming_list.item(i).text() 
                      for i in range(self.naming_list.count())]
            # 使用 Windows 风格换行，避免在记事本显示空行
            with open(self.name_format_file, 'w', encoding='utf-8') as f:
                f.write('\r\n'.join(formats))
        except Exception as e:
            print(f"保存命名格式失败: {e}")

    def get_default_naming_format(self):
        """读取默认命名格式（若失败则返回内置默认）"""
        try:
            if os.path.exists(self.default_name_format_file):
                with open(self.default_name_format_file, 'r', encoding='utf-8') as f:
                    fmt = f.read().strip()
                    if fmt and '{n}' in fmt:
                        return fmt
        except Exception as e:
            print(f"读取默认命名格式失败: {e}")
        return "图片 {n}"

    def load_default_naming_format(self):
        """加载默认命名格式到输入框并尝试选中列表项"""
        default_fmt = self.get_default_naming_format()
        self.naming_format_edit.setText(default_fmt)
        # 如果列表中有该项，则选中它
        for i in range(self.naming_list.count()):
            if self.naming_list.item(i).text() == default_fmt:
                self.naming_list.setCurrentRow(i)
                break

    def save_default_naming_format(self, fmt):
        """保存默认命名格式到文件"""
        try:
            with open(self.default_name_format_file, 'w', encoding='utf-8') as f:
                f.write(fmt)
            print(f"默认命名格式已保存: {fmt}")
        except Exception as e:
            print(f"保存默认命名格式失败: {e}")

    def set_default_naming_format(self):
        """将当前选中/输入的命名格式设为默认并保存"""
        fmt = None
        if self.naming_list.selectedItems():
            fmt = self.naming_list.selectedItems()[0].text()
        else:
            fmt = self.naming_format_edit.text().strip()
        if not fmt:
            self.show_message('警告', '请输入或选择一个命名格式')
            return
        if '{n}' not in fmt:
            self.show_message('警告', '默认命名格式必须包含 {n}')
            return
        self.save_default_naming_format(fmt)
        self.show_message('成功', f'已设置默认命名格式为：\n{fmt}')
        # 同步输入框与列表选中
        self.load_default_naming_format()

    def show_message(self, title, message, icon=QMessageBox.Information, buttons=QMessageBox.Ok):
        """统一的消息框显示方法"""
        msg = QMessageBox(self)
        msg.setWindowTitle(title)
        msg.setText(message)
        msg.setIcon(QMessageBox.NoIcon)  # 不显示任何图标
        msg.setStandardButtons(buttons)
        
        # 修改按钮文本
        if buttons & QMessageBox.Ok:
            msg.button(QMessageBox.Ok).setText('确定')
        if buttons & QMessageBox.Yes:
            msg.button(QMessageBox.Yes).setText('是')
        if buttons & QMessageBox.No:
            msg.button(QMessageBox.No).setText('否')
        if buttons & QMessageBox.Cancel:
            msg.button(QMessageBox.Cancel).setText('取消')
            
        # 设置更紧凑的样式
        msg.setStyleSheet("""
            QMessageBox {
                background-color: white;
            }
            QLabel {
                font-family: SimSun;
                font-size: 12pt;
                color: #333333;
                min-width: 150px;
                padding: 8px;
                qproperty-alignment: AlignCenter;  /* 文本居中 */
            }
            QPushButton {
                border-radius: 4px;
                padding: 4px 12px;
                background-color: #007AFF;
                color: white;
                border: none;
                font-family: SimSun;
                font-size: 12pt;
                min-width: 50px;
                min-height: 25px;
                margin: 4px;
            }
            QPushButton[text="是"] {
                background-color: #007AFF;
            }
            QPushButton[text="否"] {
                background-color: #FF3B30;
            }
            QPushButton:hover {
                background-color: #0062CC;
            }
            QPushButton[text="否"]:hover {
                background-color: #CC2F26;
            }
        """)
        
        # 调整消息框大小和位置
        msg.setFixedSize(300, 150)
        
        # 计算居中位置
        parent_geometry = self.geometry()
        x = parent_geometry.x() + (parent_geometry.width() - msg.width()) // 2
        y = parent_geometry.y() + (parent_geometry.height() - msg.height()) // 2
        msg.move(x, y)
        
        return msg.exec_()

    def load_dest_path(self):
        """加载保存的目标文件夹路径"""
        try:
            if os.path.exists(self.dest_path_file):
                with open(self.dest_path_file, 'r', encoding='utf-8') as f:
                    path = f.read().strip()
                    if path and os.path.exists(path):
                        # 确保加载的路径使用Windows风格
                        normalized_path = self.normalize_path(path)
                        self.dest_edit.setText(normalized_path)
        except Exception as e:
            print(f"加载目标路径失败: {e}")

    def normalize_path(self, path):
        """将路径统一为Windows格式"""
        return normalize_path(path)

    def save_dest_path(self, path):
        """保存目标文件夹路径"""
        try:
            # 统一路径格式为Windows格式
            normalized_path = self.normalize_path(path.strip())
            
            with open(self.dest_path_file, 'w', encoding='utf-8') as f:
                f.write(normalized_path)
            print(f"目标路径已保存到文件: {normalized_path}")
        except Exception as e:
            print(f"保存目标路径失败: {e}")

    def on_path_changed(self, line_edit, path):
        """当路径输入框内容改变时调用"""
        # 如果是目标文件夹输入框，保存路径
        if line_edit == self.dest_edit:
            # 确保路径使用Windows风格
            normalized_path = self.normalize_path(path)
            self.save_dest_path(normalized_path)

    def on_dest_path_text_changed(self, text):
        """当目标文件夹输入框文本改变时调用"""
        # 延迟保存，避免频繁写入文件
        if hasattr(self, '_save_timer'):
            self._save_timer.stop()
        else:
            from PyQt5.QtCore import QTimer
            self._save_timer = QTimer()
            self._save_timer.setSingleShot(True)
            self._save_timer.timeout.connect(lambda: self.save_dest_path(text))
        
        # 1秒后保存路径，确保使用Windows风格
        self._save_timer.start(1000)

    def select_dest_folder(self):
        """选择目标文件夹并保存路径"""
        folder = QFileDialog.getExistingDirectory(self, "选择目标文件夹")
        if folder:
            # 统一路径格式为Windows格式
            normalized_folder = self.normalize_path(folder)
            self.dest_edit.setText(normalized_folder)
            # 保存新选择的路径（会覆盖原有路径）
            self.save_dest_path(normalized_folder)

    def add_naming_format(self):
        """添加新的命名格式"""
        text = self.naming_format_edit.text().strip()
        if not text:
            self.show_message('警告', '请输入命名格式')
            return
            
        # 检查格式是否包含 {n}
        if '{n}' not in text:
            self.show_message('警告', '命名格式必须包含 {n}')
            return
            
        # 检查格式是否已存在
        for i in range(self.naming_list.count()):
            if self.naming_list.item(i).text() == text:
                self.show_message('警告', '该命名格式已存在')
                return
                
        # 检查格式是否合法
        try:
            # 尝试替换 {n} 为数字，验证格式是否有效
            test_name = text.replace('{n}', '1')
            if not test_name:
                raise ValueError('无效的命名格式')
                
            # 添加到列表
            self.naming_list.addItem(text)
            self.save_naming_formats()
            
        except Exception as e:
            self.show_message('警告', f'无效的命名格式：{str(e)}')

    def delete_naming_format(self):
        """删除选中的命名格式"""
        current_item = self.naming_list.currentItem()
        if current_item:
            result = self.show_message(
                '确认删除',
                f'确定要删除命名格式 "{current_item.text()}" 吗？',
                QMessageBox.Question,
                QMessageBox.Yes | QMessageBox.No
            )
            if result == QMessageBox.Yes:
                self.naming_list.takeItem(self.naming_list.row(current_item))
                # 删除后立即保存到文件
                self.save_naming_formats()
        else:
            self.show_message('警告', '请先选择要删除的命名格式')

    def filter_formats(self, text):
        """搜索过滤命名格式"""
        for i in range(self.naming_list.count()):
            item = self.naming_list.item(i)
            if not text or text.lower() in item.text().lower():
                item.setHidden(False)
            else:
                item.setHidden(True)

    def is_valid_id_number(self, id_num):
        """验证身份证号格式"""
        # 身份证号必须是18位
        if len(id_num) != 18:
            return False
        
        # 前17位必须是数字
        if not id_num[:17].isdigit():
            return False
        
        # 最后一位可以是数字或X（大写或小写）
        last_char = id_num[17].upper()
        if not (last_char.isdigit() or last_char == 'X'):
            return False
        
        # 验证出生日期部分（第7-14位）
        try:
            year = int(id_num[6:10])
            month = int(id_num[10:12])
            day = int(id_num[12:14])
            
            # 检查年份范围（1900-2100）
            if year < 1900 or year > 2100:
                return False
            
            # 检查月份范围
            if month < 1 or month > 12:
                return False
            
            # 检查日期范围
            if day < 1 or day > 31:
                return False
            
            # 简单的日期有效性检查
            if month in [4, 6, 9, 11] and day > 30:
                return False
            if month == 2:
                # 闰年检查
                is_leap = (year % 4 == 0 and year % 100 != 0) or (year % 400 == 0)
                if (is_leap and day > 29) or (not is_leap and day > 28):
                    return False
                    
        except ValueError:
            return False
        
        return True

    def normalize_id_number(self, id_num):
        """标准化身份证号，将小写x转换为大写X"""
        if len(id_num) == 18 and id_num[17].lower() == 'x':
            return id_num[:17] + 'X'
        return id_num

    def is_valid_name_id_format(self, line):
        """验证姓名+身份证号格式
        输入格式：姓名+身份证号
        例如：李四+110101199001011234
        返回: True 如果格式正确，False 如果格式不正确
        """
        line = line.strip()
        if not line:
            return False
        
        # 检查是否包含+
        if '+' not in line:
            return False
        
        # 用+分割
        parts = line.split('+', 1)
        name = parts[0].strip()
        id_num = parts[1].strip()
        
        # 检查姓名和身份证号是否为空
        if not name or not id_num:
            return False
        
        # 验证身份证号格式
        if not self.is_valid_id_number(id_num):
            return False
        
        return True

    def get_sorted_files(self, src_dir):
        """获取并排序文件列表"""
        try:
            # 获取选中的命名格式，如果没有选中则使用输入框中的格式
            selected_format = None
            if self.naming_list.selectedItems():
                selected_format = self.naming_list.selectedItems()[0].text()
            else:
                selected_format = self.naming_format_edit.text()
                if not selected_format or '{n}' not in selected_format:
                    selected_format = self.get_default_naming_format()  # 使用默认格式
            
            # 使用生成器获取文件列表
            def get_image_files():
                extensions = (
                    '.jpg', '.jpeg', '.png', '.bmp', '.gif',
                    '.tiff', '.tif', '.webp', '.heic', '.heif',
                    '.raw', '.cr2', '.nef', '.arw',
                    '.ico', '.jfif', '.pjpeg', '.pjp'
                )
                
                # 使用选中的格式来匹配文件
                file_pattern = re.escape(selected_format).replace(r'\{n\}', r'(\d+)')
                
                for filename in os.listdir(src_dir):
                    if filename.lower().endswith(tuple(ext.lower() for ext in extensions)):
                        base_name = os.path.splitext(filename)[0]
                        match = re.match(file_pattern, base_name)
                        if match:
                            # 确保生成的路径使用Windows风格
                            file_path = os.path.join(src_dir, filename)
                            yield self.normalize_path(file_path)
            
            # 获取并排序文件列表
            files = list(get_image_files())
            if files:
                files.sort(key=lambda x: int(re.search(
                    re.escape(selected_format).replace(r'\{n\}', r'(\d+)'),
                    os.path.splitext(os.path.basename(x))[0]
                ).group(1)))
            
            return files
            
        except Exception as e:
            self.log(f'处理文件列表时出错：{str(e)}')
            return []

def main():
    app = QApplication(sys.argv)
    window = ImageSortingApp()
    window.show()
    sys.exit(app.exec_())

if __name__ == '__main__':
    main()