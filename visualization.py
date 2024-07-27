import pyvista as pv

def setup_plotter(router):
    plotter = pv.Plotter()
    plotter.add_mesh(router.mesh, color='lightgray', opacity=0.5)
    plotter.add_text("Use buttons to interact with the model", position='upper_left')
    plotter.add_slider_widget(
        callback=router.set_max_length,
        rng=[0, 1000],
        value=1000,
        title="Max Length (mm)",
        style="modern",
        fmt="%.0f mm"
    )
    return plotter

def update_cable_path(router):
    if router.plotter is None:
        return

    # Eliminar la ruta anterior
    router.plotter.remove_actor('cable_path')
    
    if len(router.cable_points) > 1:
        points = [actor.points[0] for actor in router.cable_points]
        path = pv.PolyData(points)
        router.plotter.add_mesh(path, color='blue', line_width=5, render_lines_as_tubes=True, name='cable_path')
    
    # Actualizar la longitud del cable
    length = router.calculate_cable_length()
    router.plotter.add_text(f"Cable length: {length:.2f} mm", name='length_text', position='lower_left')

    router.plotter.render()