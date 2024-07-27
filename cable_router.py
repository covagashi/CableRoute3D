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
        self.cable_actors = []
        self.max_length = 1000  # Inicializado a 1000 mm
        self.kdtree = cKDTree(self.points)
        self.plotter = None  
        self.picking_enabled = False
        
    def setup_visualization(self):
        self.plotter = BackgroundPlotter()
        self.plotter.add_mesh(self.mesh, color='lightgray', opacity=0.5)
        
    
    # Mover la barra deslizadora a la parte inferior izquierda y hacerla más pequeña
        slider = self.plotter.add_slider_widget(
            callback=self.set_max_length,
            rng=[0, 5000],
            value=5000,
            title="Max Length (mm)",
            style="modern",
            fmt="%.0f mm",
            pointa=(0.72, 0.1), pointb=(0.9, 0.1),  # Posición y tamaño ajustados
            #font_size=8
        )
     
    
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
    
    # Añadir el widget de orientación de ejes (triad) en la esquina inferior derecha
        self.plotter.add_axes()
    
    # Inicializar el texto de la longitud del cable en la parte inferior izquierda
        self.plotter.add_text("Cable length: 0.00 mm", name='length_text', position='lower_left', font_size=10)
        
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
            self.plotter.add_text("Click to add a point", font_size=7, name="picking_instruction", position="upper_right")

    def disable_picking(self):
        if self.picking_enabled:
            self.plotter.enable_point_picking(callback=None, show_message=False)
            self.picking_enabled = False
            self.plotter.remove_actor("picking_instruction")

    def _add_point_callback(self, point):
        projected_point = project_point_to_surface(self, point)
    
        if not self.cable_points:  # Es el primer punto
            color = 'green'
        elif len(self.cable_points) == 1:  # Es el segundo punto
            # El primer punto permanece verde, el segundo es rojo
            color = 'red'
        else:
            # Cambiamos el color del punto anterior (rojo) a amarillo
            self.plotter.remove_actor(self.cable_actors[-1])
            actor = self.plotter.add_mesh(pv.PolyData(self.cable_points[-1]), 
                                          color='yellow', 
                                          point_size=15, 
                                          render_points_as_spheres=True)
            self.cable_actors[-1] = actor
            color = 'red'  # El nuevo punto será rojo

        self.cable_points.append(projected_point)
        actor = self.plotter.add_mesh(pv.PolyData(projected_point), 
                                      color=color, 
                                      point_size=15, 
                                      render_points_as_spheres=True)
        self.cable_actors.append(actor)

        if len(self.cable_points) > 1:
            self._check_and_adjust_cable_length()
    
        update_cable_path(self)
        
    def _check_and_adjust_cable_length(self):
        while self.calculate_cable_length() > self.max_length and len(self.cable_points) > 2:
            self.delete_point()
        
        if self.calculate_cable_length() > self.max_length:
            last_point = self.cable_points[-1]
            second_last_point = self.cable_points[-2]
            direction = last_point - second_last_point
            distance = np.linalg.norm(direction)
            if distance > 0:
                direction /= distance
                new_last_point = second_last_point + direction * (self.max_length - self.calculate_cable_length())
                self.cable_points[-1] = new_last_point
                self.plotter.remove_actor(self.cable_actors[-1])
                self.cable_actors[-1] = self.plotter.add_mesh(pv.PolyData(new_last_point), color='red', point_size=15, render_points_as_spheres=True)
                
    def delete_point(self):
        if self.cable_points:
            # Eliminar el último punto y su actor correspondiente
            self.cable_points.pop()
            last_actor = self.cable_actors.pop()
            self.plotter.remove_actor(last_actor)

            # Si quedan más de un punto, actualizar el color del nuevo último punto a rojo
            if len(self.cable_points) > 1:
                new_last_point = self.cable_points[-1]
                # Eliminar el actor del punto que ahora es el último
                self.plotter.remove_actor(self.cable_actors[-1])
                # Añadir un nuevo actor para el mismo punto, pero de color rojo
                new_last_actor = self.plotter.add_mesh(pv.PolyData(new_last_point), 
                                                       color='red', 
                                                       point_size=15, 
                                                       render_points_as_spheres=True)
                # Reemplazar el actor en la lista
                self.cable_actors[-1] = new_last_actor
            # Si solo queda un punto, asegurarse de que sea verde
            elif len(self.cable_points) == 1:
                self.plotter.remove_actor(self.cable_actors[0])
                new_actor = self.plotter.add_mesh(pv.PolyData(self.cable_points[0]), 
                                                  color='green', 
                                                  point_size=15, 
                                                  render_points_as_spheres=True)
                self.cable_actors[0] = new_actor

            update_cable_path(self)
            print("Último punto eliminado")
        else:
            print("No hay puntos para eliminar")

    def clear_points(self):
        for actor in self.cable_actors:
            self.plotter.remove_actor(actor)
        self.cable_points.clear()
        self.cable_actors.clear()
        update_cable_path(self)


    def calculate_cable_length(self):
        if len(self.cable_points) < 2:
            return 0.0
        
        distances = np.linalg.norm(np.diff(self.cable_points, axis=0), axis=1)
        total_length = np.sum(distances)
        return total_length
    
    def set_max_length(self, value):
        self.max_length = value
        if self.plotter:
            update_cable_path(self)
