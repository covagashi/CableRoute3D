import numpy as np
import pyvista as pv
from pyvistaqt import BackgroundPlotter
from scipy.spatial import cKDTree
from geometry_utils import discretize_shape, project_point_to_surface
from visualization import update_cable_path
from PyQt5.QtWidgets import QAction
from OCC.Extend.DataExchange import read_step_file

class CableRouter:
    def __init__(self, filename):
        self.shape = self.load_step_file(filename)
        self.points, self.faces = discretize_shape(self.shape)
        self.mesh = pv.PolyData(self.points, faces=self.faces)
        self.cable_points = []
        self.max_length = 5000  # Inicializado a 1000 mm
        self.kdtree = cKDTree(self.points)
        self.plotter = None  
        self.picking_enabled = False
        
    def setup_visualization(self):
        self.plotter = BackgroundPlotter()
        self.plotter.add_mesh(self.mesh, color='lightgray', opacity=0.5)
        
        # Añadir menú desplegable
        user_menu = self.plotter.main_menu.addMenu('Cable Routing')
        user_menu.addAction('Toggle Add Point', self.toggle_add_point)
        user_menu.addAction('Delete Last Point', self.delete_point)
        user_menu.addAction('Clear All Points', self.clear_points)

        # Añadir barra de herramientas
        user_toolbar = self.plotter.app_window.addToolBar('Cable Routing Toolbar')
        self.add_action(user_toolbar, 'Add Point', self.toggle_add_point)
        self.add_action(user_toolbar, 'Delete Point', self.delete_point)
        self.add_action(user_toolbar, 'Clear Points', self.clear_points)

        # Añadir slider
        self.plotter.add_slider_widget(
            callback=self.set_max_length,
            rng=[0, 1000],
            value=1000,
            title="Max Length (mm)",
            style="modern",
            fmt="%.0f mm"
        )
        
    def add_action(self, toolbar, key, method):
        action = QAction(key, self.plotter.app_window)
        action.triggered.connect(method)
        toolbar.addAction(action)
        
    def run(self):
        if self.plotter is None:
            self.setup_visualization()
        self.plotter.show()

    def load_step_file(self, filename):
        return read_step_file(filename)

    def toggle_add_point(self):
        if self.picking_enabled:
            self.disable_picking()
        else:
            self.enable_picking()
            
    def enable_picking(self):
        if not self.picking_enabled:
            self.plotter.enable_point_picking(callback=self._add_point_callback, show_message=True)
            self.picking_enabled = True
            self.plotter.add_text("Click to add a point", name="picking_instruction", position="upper_right")

    def disable_picking(self):
        if self.picking_enabled:
            self.plotter.enable_point_picking(callback=None, show_message=False)
            self.picking_enabled = False
            self.plotter.remove_actor("picking_instruction")

    def _add_point_callback(self, point):
        if len(self.cable_points) < 2:  # Start or end point
            projected_point = project_point_to_surface(self, point)
            color = 'green' if not self.cable_points else 'red'
        else:  # Intermediate point
            projected_point = point  # No projection for intermediate points
            color = 'yellow'
        
        actor = self.plotter.add_mesh(pv.PolyData(projected_point), color=color, point_size=15, render_points_as_spheres=True)
        self.cable_points.append(actor)
        
        if len(self.cable_points) > 1:
            self._check_and_adjust_cable_length()
        
        update_cable_path(self)
        
        # Después de añadir un punto, volvemos a habilitar el picking para el siguiente punto
        self.enable_picking()
        
    def _check_and_adjust_cable_length(self):
        while self.calculate_cable_length() > self.max_length and len(self.cable_points) > 2:
            self.delete_point()
        
        if self.calculate_cable_length() > self.max_length:
            last_point = self.cable_points[-1].points[0]
            second_last_point = self.cable_points[-2].points[0]
            direction = last_point - second_last_point
            distance = np.linalg.norm(direction)
            if distance > 0:
                direction /= distance
                new_last_point = second_last_point + direction * (self.max_length - self.calculate_cable_length())
                self.cable_points[-1].points[0] = new_last_point
                self.plotter.remove_actor(self.cable_points[-1])
                self.cable_points[-1] = self.plotter.add_mesh(pv.PolyData(new_last_point), color='red', point_size=15, render_points_as_spheres=True)
                

    def delete_point(self):
        if self.cable_points:
            last_point = self.cable_points.pop()
            self.plotter.remove_actor(last_point)
            update_cable_path(self)
            print("Last point deleted")
        else:
            print("No points to delete")

    def clear_points(self):
        for point in self.cable_points:
            self.plotter.remove_actor(point)
        self.cable_points.clear()
        update_cable_path(self)

    def calculate_cable_length(self):
        if len(self.cable_points) < 2:
            return 0.0
        
        points = [actor.points[0] for actor in self.cable_points]
        distances = np.linalg.norm(np.diff(points, axis=0), axis=1)
        total_length = np.sum(distances)
        return total_length

    def set_max_length(self, value):
        self.max_length = value
        if self.plotter:
            update_cable_path(self)
