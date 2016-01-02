from __future__ import print_function
from pyglet.gl import *


class DisplayList(object):
    """
    A class for storing the OpenGl commands for rendering an object.
    """
    def __init__(self, built=False):
        """
        Constructor
        :param built: If True, the commands have been executed
        :type built: bool
        :return:
        """
        self.built = built
        self.handle = glGenLists(1)

    def gl_compile_begin(self):
        """
        Generates the beginning of the list.
        :return:
        """
        glNewList(self.handle, GL_COMPILE)

    def gl_compile_end(self):
        """
        Generates the end of the list.
        :return:
        """
        glEndList(self.handle)
        self.built = True

    def gl_render(self):
        """
        Call all of the commands in the current list.
        :return:
        """
        try:
            glCallList(self.handle)
        except GLException as e:
            print("Got GL Exception on call list: " + str(e))
        self.built = True

    @property
    def compiled(self):
        """
        Returns whether the current list has beein completed.
        :return:
        """
        return self.built