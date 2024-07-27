import pyvista as pv

def setup_plotter(router):
    plotter = pv.Plotter()
    plotter.add_mesh(router.mesh, color='lightgray', opacity=0.5)
    plotter.add_text("Use buttons to interact with the model", position='upper_left')
    plotter.add_slider_widget(
        callback=router.set_max_length,
        rng=[0, 5000],
        value=5000,
        title="Max Length (mm)",
        style="modern",
        fmt="%.0f mm"
    )
    return plotter

def update_cable_path(self):
    if self.plotter is None:
        return

    # Eliminar la ruta anterior
    self.plotter.remove_actor('cable_path')
    
    if len(self.cable_points) > 1:
        line = pv.Line(self.cable_points[0], self.cable_points[-1], resolution=len(self.cable_points)-1)
        line.points = self.cable_points
        tube = line.tube(radius=2)
        self.plotter.add_mesh(tube, color='blue', name='cable_path', render_lines_as_tubes=True, line_width=5)
    
    # Actualizar la longitud del cable
    length = self.calculate_cable_length()
    self.plotter.remove_actor('length_text')
    self.plotter.add_text(f"Cable length: {length:.2f} mm", name='length_text', position='lower_left', font_size=10)

    self.plotter.render()