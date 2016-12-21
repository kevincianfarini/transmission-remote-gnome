# torrent_list_view.py
#
# Copyright (C) 2016 Patrick Griffis <tingping@tingping.se>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import logging
from enum import IntEnum
from collections import (OrderedDict, namedtuple)
from functools import partial
from gettext import gettext as _

from gi.repository import (
	GLib,
	GObject,
	Gio,
	Pango,
	Gdk,
	Gtk,
)

from .client import Client
from .list_wrapper import WrappedStore
from .torrent_file_view import CellRendererSize
from .gi_composites import GtkTemplate
from .torrent import TorrentStatus


@GtkTemplate(ui='/se/tingping/Trg/ui/torrentview.ui')
class TorrentListView(Gtk.TreeView):
	__gtype_name__ = 'TorrentListView'

	client = GObject.Property(type=Client, flags=GObject.ParamFlags.READWRITE|GObject.ParamFlags.CONSTRUCT_ONLY)

	def __init__(self, model, **kwargs):
		# NOTE: Order must match TorrentColumn enum
		props = OrderedDict()
		props['name'] = str
		props['size-when-done'] = GObject.TYPE_UINT64
		props['percent-done'] = float
		props['rate-download'] = GObject.TYPE_UINT64
		props['rate-upload'] = GObject.TYPE_UINT64
		props['status'] = GObject.TYPE_UINT64
		store = WrappedStore.new_for_model(model, props)
		self.filter_model = Gtk.TreeModelFilter(child_model=store)
		self._sort_model = Gtk.TreeModelSort(model=self.filter_model)

		super().__init__(model=self._sort_model, **kwargs)
		self.init_template()

	def do_button_press_event(self, event: Gdk.EventButton) -> int:
		if not (event.type == Gdk.EventType.BUTTON_PRESS and event.button == Gdk.BUTTON_SECONDARY):
			return Gtk.TreeView.do_button_press_event(self, event)

		ret = self.get_path_at_pos(event.x, event.y)
		if not ret or not ret[0]:
			return Gdk.EVENT_STOP

		# If we right click a single unselcted item, select it.
		path = ret[0]
		selection = self.get_selection()
		if not selection.path_is_selected(path):
			selection.unselect_all()
			selection.select_path(path)

		# But we handle multple selections
		model, paths = selection.get_selected_rows()
		torrents = []
		for path in paths:
			it = model.get_iter(path)
			torrent = model[it][-1]
			torrents.append(torrent)

		menu = self._build_menu(torrents)
		if hasattr(menu, 'popup_at_pointer'):
			menu.popup_at_pointer(event) # Gtk 3.22
		else:
			menu.popup(None, None, None, None, event.button, event.time)
		return Gdk.EVENT_STOP

	def _build_menu(self, torrents) -> Gio.Menu:
		Entry = namedtuple('Entry', ['label', 'function'])

		MENU_ITEMS = (
			Entry(_('Resume'), partial(self.client.torrent_start, torrents)),
			Entry(_('Pause'), partial(self.client.torrent_stop, torrents)),
			Entry(_('Verify'), partial(self.client.torrent_verify, torrents)),
			(),
			# Entry(_('Move'), None),
			Entry(_('Remove'), partial(self.client.torrent_remove, torrents)),
			Entry(_('Delete'), partial(self.client.torrent_remove, torrents, True)),
		)

		def on_activate(widget, callback):
			callback()
			self.client.refresh()

		menu = Gtk.Menu.new()
		for entry in MENU_ITEMS:
			if entry:
				item = Gtk.MenuItem.new_with_label(entry.label)
				if entry.function:
					item.connect('activate', on_activate, entry.function)
			else:
				item = Gtk.SeparatorMenuItem.new()
			menu.append(item)

		menu.attach_to_widget(self)
		menu.show_all()
		return menu


class TorrentColumn(IntEnum):
	name = 0
	size = 1
	progress = 2
	down = 3
	up = 4
	status = 5


class CellRendererSpeed(Gtk.CellRendererText):
	__gtype_name__ = 'TrgCellRendererSpeed'

	speed = GObject.Property(type=GObject.TYPE_UINT64)

	def __init__(self, **kwargs):
		super().__init__(text='', **kwargs)
		self.connect('notify::speed', self._on_speed_change)

	def _on_speed_change(self, prop, param):
		if self.speed:
			self.props.text = GLib.format_size(self.speed) + '/s'
		else:
			self.props.text = ''


class CellRendererPercent(Gtk.CellRendererProgress):
	__gtype_name__ = 'TrgCellRendererPercent'

	percent = GObject.Property(type=float)

	def __init__(self, **kwargs):
		super().__init__(**kwargs)
		self.connect('notify::percent', self._on_percent_change)

	def _on_percent_change(self, prop, param):
		self.props.value = int(self.percent * 100)


STATUS_ICONS = {
	TorrentStatus.STOPPED: Gio.ThemedIcon.new('media-playback-pause-symbolic'),
	TorrentStatus.DOWNLOAD: Gio.ThemedIcon.new('network-transmit-receive-symbolic'),
	TorrentStatus.SEED: Gio.ThemedIcon.new('network-transmit-symbolic'),
	TorrentStatus.CHECK: Gio.ThemedIcon.new('emblem-synchronizing-symbolic'),

	TorrentStatus.CHECK_WAIT: Gio.ThemedIcon.new('content-loading-symbolic'),
	TorrentStatus.DOWNLOAD_WAIT: Gio.ThemedIcon.new('content-loading-symbolic'),
	TorrentStatus.SEED_WAIT: Gio.ThemedIcon.new('content-loading-symbolic'),
}


class CellRendererStatus(Gtk.CellRendererPixbuf):
	__gtype_name__ = 'TrgCellRendererStatus'

	status = GObject.Property(type=GObject.TYPE_UINT64)

	def __init__(self, **kwargs):
		super().__init__(gicon=None, **kwargs)
		self.connect('notify::status', self._on_status_change)

	def _on_status_change(self, prop, param):
		icon = STATUS_ICONS.get(self.props.status)
		self.props.gicon = icon
		if not icon:
			logging.warning('Icon for status {} not found!'.format(self.props.status))
