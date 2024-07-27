from cable_router import CableRouter

def main():
    filename = r"C:\Users\daviann\Documents\CableRoute3D\examples\1018.000.stp"
    router = CableRouter(filename)
    router.setup_visualization()
    router.plotter.app.exec_()

if __name__ == "__main__":
    main()
