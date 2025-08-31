import sys
import json
import uuid
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QGraphicsView, QGraphicsScene, QGraphicsItem,
    QGraphicsTextItem, QDialog, QVBoxLayout, QHBoxLayout, QLineEdit, QTextEdit,
    QPushButton, QColorDialog, QFormLayout, QDateEdit, QComboBox, QMessageBox,
    QGraphicsProxyWidget, QStyleOptionGraphicsItem, QWidget, QMenu
)
from PyQt6.QtCore import Qt, QPointF, QRectF, QDate, QLineF
from PyQt6.QtGui import QColor, QBrush, QPen, QPainter, QPainterPath, QFont

# --- CONFIGURATION ---
SAVE_FILE = 'tasks.json'
DEFAULT_NODE_COLOR = '#ffc107'  # A nice amber color

class TaskNode(QGraphicsItem):
    """
    Represents a draggable, editable task node in the graphics scene.
    """
    def __init__(self, task_data, main_window):
        super().__init__()
        self.task_data = task_data
        self.main_window = main_window
        self.width = 200
        self.height = 80
        self.lines = [] # To store connected lines

        self.setFlags(
            QGraphicsItem.GraphicsItemFlag.ItemIsMovable |
            QGraphicsItem.GraphicsItemFlag.ItemIsSelectable |
            QGraphicsItem.GraphicsItemFlag.ItemSendsGeometryChanges
        )
        self.setCacheMode(QGraphicsItem.CacheMode.DeviceCoordinateCache)
        self.setZValue(1)

        # Set initial position
        pos = self.task_data.get('pos', [10, 10])
        self.setPos(QPointF(pos[0], pos[1]))
        
        # Create text items as children
        self.title = QGraphicsTextItem(self)
        self.title.setDefaultTextColor(Qt.GlobalColor.black)
        
        self.details = QGraphicsTextItem(self)
        self.details.setDefaultTextColor(QColor("#495057")) # A dark gray

        self.update_display()

    def boundingRect(self):
        """Defines the outer boundaries of the item."""
        return QRectF(0, 0, self.width, self.height)

    def paint(self, painter, option, widget=None):
        """Paints the node's appearance."""
        path = QPainterPath()
        path.addRoundedRect(self.boundingRect(), 10, 10)

        # Set color
        color = QColor(self.task_data.get('color', DEFAULT_NODE_COLOR))
        painter.setBrush(QBrush(color))
        
        # Add a border if selected
        if self.isSelected():
            pen = QPen(Qt.GlobalColor.darkBlue, 3)
            pen.setStyle(Qt.PenStyle.DotLine)
            painter.setPen(pen)
        else:
             painter.setPen(QPen(Qt.GlobalColor.black, 1))

        painter.drawPath(path)
        
    def update_display(self):
        """Updates the text and tooltip based on task_data."""
        # --- Title ---
        font = QFont("Inter", 10, QFont.Weight.Bold)
        self.title.setFont(font)
        self.title.setPlainText(self.task_data['title'])
        self.title.setPos(10, 5)
        
        # --- Dates ---
        details_font = QFont("Inter", 8)
        self.details.setFont(details_font)
        
        created_str = self.task_data.get('created_date', 'N/A')
        due_str = self.task_data.get('due_date', 'N/A')
        
        details_text = f"Created: {created_str}\nDue:       {due_str}"
        self.details.setPlainText(details_text)
        self.details.setPos(10, 35)

        # --- Tooltip ---
        self.setToolTip(f"Description: {self.task_data.get('description', 'N/A')}\n"
                        f"Category: {self.task_data.get('category', 'N/A')}")
    
    def add_line(self, line):
        """Registers a connection line with this node."""
        if line not in self.lines:
            self.lines.append(line)

    def remove_line(self, line):
        """Unregisters a connection line."""
        try:
            self.lines.remove(line)
        except ValueError:
            pass # Line not found

    def itemChange(self, change, value):
        """Called when the item's state changes, e.g., it's moved."""
        if change == QGraphicsItem.GraphicsItemChange.ItemPositionHasChanged:
            # Update the position in the data model
            self.task_data['pos'] = [self.pos().x(), self.pos().y()]
            # Update all connected lines
            for line in self.lines:
                line.update_position()
            self.main_window.save_data() # Save on move
        return super().itemChange(change, value)

    def mouseDoubleClickEvent(self, event):
        """Opens the detail editor on double-click."""
        dialog = TaskDialog(self.task_data, self.parentWidget())
        result = dialog.exec()

        if result == QDialog.DialogCode.Accepted:
            self.task_data.update(dialog.get_data())
            self.update_display()
            self.main_window.save_data()
        elif result == 100: # Custom code for deletion
            self.main_window.delete_task(self)
            
        super().mouseDoubleClickEvent(event)
        
    def contextMenuEvent(self, event):
        """Handles right-click for connecting nodes."""
        self.main_window.node_context_menu(self, event)

class ConnectionLine(QGraphicsItem):
    """A line that connects two TaskNodes."""
    def __init__(self, start_node, end_node, connection_data, main_window):
        super().__init__()
        self.start_node = start_node
        self.end_node = end_node
        self.connection_data = connection_data
        self.main_window = main_window
        self.arrow_size = 15

        self.setZValue(0) # Ensure lines are drawn below nodes
        self.start_node.add_line(self)
        self.end_node.add_line(self)
        self.update_position()

    def BoundingRect(self):
        return self.shape().controlPointRect()

    def shape(self):
        path = QPainterPath()
        path.moveTo(self.line.p1())
        path.lineTo(self.line.p2())
        return path

    def paint(self, painter, option, widget=None):
        """Paints the line and arrowhead."""
        if self.start_node is None or self.end_node is None:
            return

        pen = QPen(Qt.GlobalColor.black, 2, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin)
        painter.setPen(pen)

        # Draw main line
        painter.drawLine(self.line)

        # Draw arrowhead
        angle = self.line.angle()
        dest_arrow_p1 = self.line.p2() + QPointF(self.arrow_size * 0.707 * 2, 0).rotated(angle - 135)
        dest_arrow_p2 = self.line.p2() + QPointF(self.arrow_size * 0.707 * 2, 0).rotated(angle + 135)

        painter.setBrush(QBrush(Qt.GlobalColor.black))
        painter.drawPolygon(QPointF(self.line.p2()), dest_arrow_p1, dest_arrow_p2)

    def update_position(self):
        """Recalculates the line's start and end points based on node positions."""
        self.prepareGeometryChange()
        start_center = self.start_node.pos() + self.start_node.boundingRect().center()
        end_center = self.end_node.pos() + self.end_node.boundingRect().center()
        self.line = QLineF(start_center, end_center)
        self.update()

    def contextMenuEvent(self, event):
        """Provides an option to delete the connection."""
        menu = QMenu()
        delete_action = menu.addAction("Delete Connection")
        action = menu.exec(event.screenPos())
        if action == delete_action:
            self.main_window.delete_connection(self)


class TaskDialog(QDialog):
    """
    A dialog window for creating and editing task details.
    """
    def __init__(self, task_data=None, parent=None):
        super().__init__(parent)
        self.task_data = task_data if task_data else {}
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle("Task Details")
        self.setMinimumWidth(350)
        layout = QVBoxLayout(self)
        form_layout = QFormLayout()

        self.title_edit = QLineEdit(self.task_data.get('title', ''))
        self.desc_edit = QTextEdit(self.task_data.get('description', ''))
        self.desc_edit.setFixedHeight(100)
        
        # Due Date
        self.date_edit = QDateEdit()
        self.date_edit.setCalendarPopup(True)
        due_date_str = self.task_data.get('due_date')
        if due_date_str:
            self.date_edit.setDate(QDate.fromString(due_date_str, "yyyy-MM-dd"))
        else:
            self.date_edit.setDate(QDate.currentDate())

        self.category_edit = QComboBox()
        self.category_edit.addItems(["Work", "Personal", "Urgent", "Study", "Other"])
        self.category_edit.setCurrentText(self.task_data.get('category', 'Work'))
        
        # Color Picker
        self.color_button = QPushButton("Choose Color")
        self.current_color = QColor(self.task_data.get('color', DEFAULT_NODE_COLOR))
        self.color_button.setStyleSheet(f"background-color: {self.current_color.name()};")
        self.color_button.clicked.connect(self.choose_color)

        form_layout.addRow("Title:", self.title_edit)
        form_layout.addRow("Description:", self.desc_edit)
        form_layout.addRow("Due Date:", self.date_edit)
        form_layout.addRow("Category:", self.category_edit)
        form_layout.addRow("Color:", self.color_button)

        layout.addLayout(form_layout)
        
        # Action Buttons
        button_layout = QHBoxLayout()
        self.save_button = QPushButton("Save")
        self.save_button.clicked.connect(self.accept)
        
        self.delete_button = QPushButton("Delete Task")
        self.delete_button.setStyleSheet("background-color: #dc3545; color: white;")
        self.delete_button.clicked.connect(self.handle_delete)

        if 'id' not in self.task_data: # Hide delete for new tasks
            self.delete_button.hide()
            
        button_layout.addWidget(self.delete_button)
        button_layout.addStretch()
        button_layout.addWidget(self.save_button)
        layout.addLayout(button_layout)
        
    def choose_color(self):
        color = QColorDialog.getColor(self.current_color, self, "Select Task Color")
        if color.isValid():
            self.current_color = color
            self.color_button.setStyleSheet(f"background-color: {self.current_color.name()};")

    def handle_delete(self):
        reply = QMessageBox.question(self, 'Confirm Deletion',
                                     "Are you sure you want to delete this task?",
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                                     QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            # We use a custom result code to signal deletion
            self.done(100) # Custom code for deletion

    def get_data(self):
        return {
            "title": self.title_edit.text(),
            "description": self.desc_edit.toPlainText(),
            "due_date": self.date_edit.date().toString("yyyy-MM-dd"),
            "category": self.category_edit.currentText(),
            "color": self.current_color.name(),
        }

class FlowChartView(QGraphicsView):
    """Custom QGraphicsView to handle background drawing and mouse events."""
    def __init__(self, scene, parent=None):
        super().__init__(scene, parent)
        self.main_window = parent
        self.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.setDragMode(QGraphicsView.DragMode.RubberBandDrag)
        self.start_node_for_connection = None

    def drawBackground(self, painter, rect):
        """Draws a grid background."""
        super().drawBackground(painter, rect)
        grid_size = 25
        left = int(rect.left())
        right = int(rect.right())
        top = int(rect.top())
        bottom = int(rect.bottom())

        left_grid = left - (left % grid_size)
        top_grid = top - (top % grid_size)

        pen = QPen(QColor(220, 220, 220), 1)
        painter.setPen(pen)

        for x in range(left_grid, right, grid_size):
            painter.drawLine(x, top, x, bottom)
        for y in range(top_grid, bottom, grid_size):
            painter.drawLine(left, y, right, y)
    
    def node_context_menu(self, node, event):
        """Handle right-click on a node."""
        if self.start_node_for_connection is None:
            # Start a new connection
            self.start_node_for_connection = node
            node.setSelected(True) # Visually indicate start node
        else:
            # End the connection
            if self.start_node_for_connection != node:
                self.main_window.add_connection(self.start_node_for_connection, node)
            self.start_node_for_connection.setSelected(False)
            self.start_node_for_connection = None

    def mousePressEvent(self, event):
        """Handle mouse press to cancel connection drawing."""
        if event.button() == Qt.MouseButton.LeftButton and self.start_node_for_connection:
            self.start_node_for_connection.setSelected(False)
            self.start_node_for_connection = None
        super().mousePressEvent(event)


class MainWindow(QMainWindow):
    """
    The main application window.
    """
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Stateful Task Tracker")
        self.setGeometry(100, 100, 1200, 800)

        self.scene = QGraphicsScene(self)
        self.view = FlowChartView(self.scene, self)
        self.setCentralWidget(self.view)

        self.nodes = {} # task_id -> TaskNode instance
        self.connections = {} # conn_id -> ConnectionLine instance

        self.setup_ui()
        self.load_data()

    def setup_ui(self):
        # Using a floating button for adding tasks
        self.add_button = QPushButton("+ Add Task", self)
        self.add_button.setStyleSheet("""
            QPushButton {
                background-color: #007bff;
                color: white;
                font-size: 16px;
                padding: 10px;
                border-radius: 22px;
                border: none;
            }
            QPushButton:hover {
                background-color: #0056b3;
            }
        """)
        self.add_button.setFixedSize(150, 45)
        self.add_button.clicked.connect(self.add_task)
    
    def resizeEvent(self, event):
        """Ensure the add button stays in the bottom-right corner."""
        super().resizeEvent(event)
        btn_size = self.add_button.size()
        self.add_button.move(self.width() - btn_size.width() - 20,
                             self.height() - btn_size.height() - 20)

    def add_task(self):
        """Opens a dialog to create a new task and adds it to the scene."""
        dialog = TaskDialog(parent=self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            task_data = dialog.get_data()
            task_data['id'] = str(uuid.uuid4())
            task_data['pos'] = [20, 20] # Default position for new tasks
            task_data['created_date'] = QDate.currentDate().toString("yyyy-MM-dd")
            
            node = TaskNode(task_data, self)
            self.scene.addItem(node)
            self.nodes[task_data['id']] = node
            self.save_data()
    
    def delete_task(self, node_to_delete):
        """Deletes a task node and its connections."""
        task_id = node_to_delete.task_data['id']
        
        # Remove associated connections
        lines_to_remove = list(node_to_delete.lines)
        for line in lines_to_remove:
            self.delete_connection(line)
            
        # Remove the node itself
        self.scene.removeItem(node_to_delete)
        if task_id in self.nodes:
            del self.nodes[task_id]
        
        self.save_data()
        
    def add_connection(self, start_node, end_node):
        """Adds a visual and logical connection between two nodes."""
        start_id = start_node.task_data['id']
        end_id = end_node.task_data['id']

        # Prevent duplicate connections
        for conn in self.connections.values():
            if (conn.connection_data['from'] == start_id and conn.connection_data['to'] == end_id):
                return
        
        conn_id = str(uuid.uuid4())
        conn_data = {'id': conn_id, 'from': start_id, 'to': end_id}
        
        line = ConnectionLine(start_node, end_node, conn_data, self)
        self.scene.addItem(line)
        self.connections[conn_id] = line
        self.save_data()

    def delete_connection(self, line_to_delete):
        """Deletes a connection line."""
        conn_id = line_to_delete.connection_data['id']

        line_to_delete.start_node.remove_line(line_to_delete)
        line_to_delete.end_node.remove_line(line_to_delete)
        
        self.scene.removeItem(line_to_delete)
        if conn_id in self.connections:
            del self.connections[conn_id]

        self.save_data()

    def save_data(self):
        """Saves all task and connection data to a JSON file."""
        tasks = [node.task_data for node in self.nodes.values()]
        connections = [line.connection_data for line in self.connections.values()]
        
        data_to_save = {
            "tasks": tasks,
            "connections": connections
        }
        
        try:
            with open(SAVE_FILE, 'w') as f:
                json.dump(data_to_save, f, indent=4)
        except IOError as e:
            print(f"Error saving data: {e}")

    def load_data(self):
        """Loads data from the JSON file and populates the scene."""
        try:
            with open(SAVE_FILE, 'r') as f:
                data = json.load(f)
                
                # Load tasks
                for task_data in data.get('tasks', []):
                    node = TaskNode(task_data, self)
                    self.scene.addItem(node)
                    self.nodes[task_data['id']] = node

                # Load connections
                for conn_data in data.get('connections', []):
                    start_node = self.nodes.get(conn_data['from'])
                    end_node = self.nodes.get(conn_data['to'])
                    if start_node and end_node:
                        line = ConnectionLine(start_node, end_node, conn_data, self)
                        self.scene.addItem(line)
                        self.connections[conn_data['id']] = line
                        
        except FileNotFoundError:
            print(f"'{SAVE_FILE}' not found. Starting with a blank canvas.")
        except (json.JSONDecodeError, IOError) as e:
            print(f"Error loading or parsing data: {e}")

    def node_context_menu(self, node, event):
        """Proxy method to call the view's context menu handler."""
        self.view.node_context_menu(node, event)

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())

