# Transmission Remote Gnome

Remote client for Transmission.

The goal of the project is to modernize [transmission-remote-gtk](https://github.com/transmission-remote-gtk/transmission-remote-gtk)
project in terms of UI and codebase. This is still a work in progress.

## Installing

### Fedora

```
sudo dnf copr enable tingping/transmission-remote-gnome
sudo dnf install transmission-remote-gnome
```

### Flatpak

```
flatpak install https://dl.tingping.se/flatpak/transmission-remote-gnome.flatpakref
```

## Building

### Dependencies

- Meson >= 0.40.0 (build only)
- Python >= 3.4
- PyGObject
- GLib (Only 2.50+ tested)
- Gtk3 (Only 3.20+ tested)
- LibSoup


```sh
meson build
ninja -C build
sudo ninja -C build install
```
