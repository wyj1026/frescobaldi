# This file is part of the qpopplerview package.
#
# Copyright (c) 2010, 2011 by Wilbert Berendsen
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301  USA
# See http://www.gnu.org/licenses/ for more information.


"""
View widget to display PDF documents.
"""


from PyQt4.QtCore import *
from PyQt4.QtGui import *

import popplerqt4

from . import surface
from . import cache

from . import (
    # viewModes:
    FixedScale,
    FitWidth,
    FitHeight,
    FitBoth,
)


class View(QScrollArea):
    
    viewModeChanged = pyqtSignal(int)
    
    def __init__(self, parent=None):
        super(View, self).__init__(parent)
        
        self.setAlignment(Qt.AlignCenter)
        self.setBackgroundRole(QPalette.Dark)

        self._viewMode = FixedScale
        
        # delayed resize
        self._newsize = None
        self._resizeTimer = QTimer(singleShot = True, timeout = self._resizeTimeout)
        self._oldsize = None
        
    def surface(self):
        """Returns our Surface, the widget drawing the page(s)."""
        sf = self.widget()
        if not sf:
            sf = surface.Surface(self)
            self.setSurface(sf)
        return sf
    
    def setSurface(self, sf):
        """Sets the given surface as our widget."""
        self.setWidget(sf)
    
    def viewMode(self):
        """Returns the current ViewMode."""
        return self._viewMode
        
    def setViewMode(self, mode):
        """Sets the current ViewMode."""
        if mode == self._viewMode:
            return
        self._viewMode = mode
        if mode:
            # change view
            self.surface().pageLayout().fit(self.viewport().size(), mode)
            self.surface().pageLayout().update()
            self.surface().updateLayout()
        self.viewModeChanged.emit(mode)
    
    def load(self, document):
        """Convenience method to load all the pages from the given Poppler.Document."""
        self.surface().pageLayout().load(document)
        self.surface().pageLayout().update()
        self.surface().updateLayout()

    def clear(self):
        """Convenience method to clear the current layout."""
        self.surface().pageLayout().clear()
        self.surface().pageLayout().update()
        self.surface().updateLayout()

    def setScale(self, scale):
        """Sets the scale of all pages in the View."""
        self.setViewMode(FixedScale)
        self.surface().pageLayout().setScale(scale)
        self.surface().pageLayout().update()
        self.surface().updateLayout()

    def visiblePages(self):
        """Yields the visible pages."""
        rect = self.viewport().rect()
        rect.translate(-self.surface().pos())
        rect.intersect(self.surface().rect())
        return self.surface().pageLayout().pagesAt(rect)

    def redraw(self):
        """Redraws, e.g. when you changed rendering hints or papercolor on the document."""
        pages = list(self.visiblePages())
        documents = set(page.document() for page in pages)
        for document in documents:
            cache.clear(document)
        for page in pages:
            cache.generate(page)

    def resizeEvent(self, ev):
        super(View, self).resizeEvent(ev)
        if self.viewMode() and self.surface().pageLayout().count():
            # Detect a resize loop due to scrollbar dis- and re-appearing
            # When the area size does not change and both scrollbars disappear
            # at the same time, a resize of the surface would case one of the
            # scrollbars to appear again, causing a resize again, etc.
            if (self.size() == self._oldsize
                and ev.size().width() > ev.oldSize().width()
                and ev.size().height() > ev.oldSize().height()):
                # We are in a resize loop.
                # Compute the largest possible surface that would fit in the
                # scrollarea without causing the scrollbars to appear again.
                # We use a sequential algorithm that could be improved to a
                # binary method, but it doesn't happen often and uses at most
                # scrollbar-width (approx. 15) iterations.
                def sizes():
                    """Yields sizes to try."""
                    s = QSize(ev.size()) # copy
                    if self.viewMode() & FitWidth:
                        for width in range(ev.size().width(), self.surface().width(), -1):
                            s.setWidth(width)
                            yield s
                    else:
                        for height in range(ev.size().height(), self.surface().height(), -1):
                            s.setHeight(height)
                            yield s
                layout = self.surface().pageLayout()
                for size in sizes():
                    layout.fit(size, self.viewMode())
                    layout.update()
                    if (layout.size().width() <= ev.size().width()
                        and layout.size().height() <= ev.size().height()):
                        # directly update it, it will not cause a new resize event
                        break
                else:
                    # reset layout, just to be sure
                    layout.fit(self.surface().size(), self.viewMode())
                    layout.update()
                self.surface().updateLayout()
            else:
                self._resizeTimer.start(100)
        self._oldsize = self.size()
            
    def _resizeTimeout(self):
        self.surface().pageLayout().fit(self.viewport().size(), self.viewMode())
        self.surface().pageLayout().update()
        self.surface().updateLayout()


