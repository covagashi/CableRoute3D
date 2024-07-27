import numpy as np
from OCC.Core.BRepMesh import BRepMesh_IncrementalMesh
from OCC.Core.TopExp import TopExp_Explorer
from OCC.Core.TopAbs import TopAbs_FACE
from OCC.Core.TopoDS import topods
from OCC.Core.TopLoc import TopLoc_Location
from OCC.Core.BRep import BRep_Tool
from OCC.Core.BRepBuilderAPI import BRepBuilderAPI_MakeVertex
from OCC.Core.BRepExtrema import BRepExtrema_DistShapeShape
from OCC.Core.gp import gp_Pnt

def discretize_shape(shape, resolution=1.0):
    mesh = BRepMesh_IncrementalMesh(shape, resolution)
    mesh.Perform()
    
    points = []
    faces = []
    explorer = TopExp_Explorer()
    explorer.Init(shape, TopAbs_FACE)
    
    while explorer.More():
        face = topods.Face(explorer.Current())
        location = TopLoc_Location()
        triangulation = BRep_Tool().Triangulation(face, location)
        
        if triangulation is not None:
            transform = location.Transformation()
            for i in range(1, triangulation.NbTriangles() + 1):
                triangle = triangulation.Triangle(i)
                triangle_points = []
                for j in range(1, 4):
                    node = triangulation.Node(triangle.Value(j))
                    point = node.Transformed(transform)
                    points.append([point.X(), point.Y(), point.Z()])
                    triangle_points.append(len(points) - 1)
                # Añadir el número de puntos en la cara (3 para triángulos) antes de los índices
                faces.extend([3] + triangle_points)
        
        explorer.Next()
    
    return np.array(points), faces

def project_point_to_surface(router, point):
    _, idx = router.kdtree.query(point)
    closest_point = router.points[idx]
    
    vertex = BRepBuilderAPI_MakeVertex(gp_Pnt(*closest_point)).Vertex()
    distance = BRepExtrema_DistShapeShape(router.shape, vertex)
    
    if distance.IsDone():
        return np.array(distance.PointOnShape1(1).Coord())
    return np.array(closest_point)
