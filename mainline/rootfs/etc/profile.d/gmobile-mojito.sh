# Redmi Note 10 (mojito) display cutout / rounded corners for Phosh and phoc, without rebuilding gmobile:
# GLib resource overlay so gmobile's lookup of devices/display-panels/xiaomi,mojito.json finds our file
# (other devices' panels still come from gmobile's built-in resources). A rebuilt gmobile with the file
# compiled in (mainline/gmobile, 0.7.5-r1) froze the phone at session start; stock gmobile + this works.
_gm_overlay="/mobi/phosh/gmobile/devices/display-panels=/usr/share/gmobile-mojito/display-panels"
case ":${G_RESOURCE_OVERLAYS}:" in
	*":${_gm_overlay}:"*) ;;
	*) export G_RESOURCE_OVERLAYS="${_gm_overlay}${G_RESOURCE_OVERLAYS:+:$G_RESOURCE_OVERLAYS}" ;;
esac
unset _gm_overlay
