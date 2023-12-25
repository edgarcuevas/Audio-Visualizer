import numpy as np
from opensimplex import OpenSimplex
import pyqtgraph.opengl as gl
from pyqtgraph.Qt import QtCore, QtWidgets
import struct
import pyaudio
import sys


class Terrain(object):
    """
    Represents a terrain object for audio visualization.

    Attributes:
        app (QtWidgets.QApplication): The Qt application instance.
        window (gl.GLViewWidget): The OpenGL view widget.
        nsteps (float): The step size for generating terrain points.
        offset (float): The offset value for terrain generation.
        ypoints (numpy.ndarray): The array of y-coordinates for terrain points.
        xpoints (numpy.ndarray): The array of x-coordinates for terrain points.
        nfaces (int): The number of faces in the terrain.
        RATE (int): The audio sample rate.
        CHUNK (int): The audio chunk size.
        p (pyaudio.PyAudio): The PyAudio instance.
        stream (pyaudio.Stream): The audio stream.
        noise (OpenSimplex): The noise generator for terrain height.
        mountains (gl.GLMeshItem): The mesh item representing the mountains.
    """

    def __init__(self):
        """
        Initializes a Terrain object.
        """
        self.app = QtWidgets.QApplication(sys.argv)
        self.window = gl.GLViewWidget()
        self.window.setWindowTitle("Visualiser")
        self.window.setGeometry(0, 110, 1920, 1080)
        self.window.setCameraPosition(distance=35, elevation=15)
        self.window.show()

        self.nsteps = 1.3
        self.offset = 0
        self.ypoints = np.arange(-20, 20 + self.nsteps, self.nsteps)
        self.xpoints = np.arange(-20, 20 + self.nsteps, self.nsteps)
        self.nfaces = len(self.ypoints)

        self.RATE = 44100
        self.CHUNK = len(self.xpoints) * len(self.ypoints)

        self.p = pyaudio.PyAudio()
        self.stream = self.p.open(
            format=pyaudio.paInt16,
            channels=1,
            rate=self.RATE,
            input=True,
            output=True,
            frames_per_buffer=self.CHUNK,
        )

        # seed = uuid.uuid1().int>>64 # -> randomise seed.
        self.noise = OpenSimplex(seed=0)

        verts, faces, colors = self.mesh()

        self.mountains = gl.GLMeshItem(
            faces=faces,
            vertexes=verts,
            drawEdges=True,
            smooth=False,
            edgeColor=(0.1, 0.6, 0, 1),  # green
        )
        self.mountains.setGLOptions("translucent")
        self.window.addItem(self.mountains)

    def mesh(self, offset=0, height=1.5, waveform=None):
        """
        Generates a mesh based on the given parameters.

        Args:
            offset (float): The offset value for the noise function.
            height (float): The height of the mesh.
            waveform (bytes): The waveform data.

        Returns:
            tuple: A tuple containing the vertices, faces, and colors of the mesh.
        """
        if waveform is not None:
            waveform = struct.unpack(str(2 * self.CHUNK) + "B", waveform)
            waveform = np.array(waveform, dtype="b")[::2] + 128
            waveform = np.array(waveform, dtype="int32") - 128
            waveform = waveform * 0.02
            waveform = waveform.reshape((len(self.xpoints), len(self.ypoints)))
        else:
            waveform = np.array([1] * 1024)
            waveform = waveform.reshape((len(self.xpoints), len(self.ypoints)))

        faces = []
        colors = []
        verts = np.array(
            [
                [
                    x,
                    y,
                    waveform[xid][yid]
                    * self.noise.noise2(
                        x=xid / 5 + self.offset, y=yid / 5 + self.offset
                    ),
                ]
                for xid, x in enumerate(self.xpoints)
                for yid, y in enumerate(self.ypoints)
            ]
        )

        for yid in range(self.nfaces - 1):
            yoffset = yid * self.nfaces
            for xid in range(self.nfaces - 1):
                faces.append(
                    [
                        xid + yoffset,
                        xid + yoffset + self.nfaces,
                        xid + yoffset + self.nfaces + 1,
                    ]
                )
                faces.append(
                    [
                        xid + yoffset,
                        xid + yoffset + 1,
                        xid + yoffset + self.nfaces + 1,
                    ]
                )
                colors.append([0.1, 0.3, 0, 0.35])  # (0.1,0.6,0,1) green
                colors.append([0.09, 0.3, 0, 0.35])

        faces = np.array(faces)
        colors = np.array(colors)

        return verts, faces, colors

    def update(self):
        """
        Updates the visualization by reading audio data, generating mesh data, and setting the mesh data for the mountains.

        Parameters:
        None

        Returns:
        None
        """
        wf_data = self.stream.read(self.CHUNK)
        verts, faces, colors = self.mesh(offset=self.offset, waveform=wf_data)
        self.mountains.setMeshData(vertexes=verts, faces=faces, faceColors=colors)
        self.offset -= 0.059

    def start(self):
        """
        Starts the application.

        If running in interactive mode or if PyQt is not installed, this method starts the QApplication event loop.
        """
        if (sys.flags.interactive != 1) or not hasattr(QtCore, "PYQT_VERSION"):
            QtWidgets.QApplication.instance().exec_()

    def animation(self, frametime=120):
        """
        Starts the animation loop with the specified frame time.

        Parameters:
            frametime (int): The time interval between each frame in milliseconds. Default is 120ms.
        """
        timer = QtCore.QTimer()
        timer.timeout.connect(self.update)
        timer.start(frametime)
        self.start()


if __name__ == "__main__":
    t = Terrain()
    t.animation()
