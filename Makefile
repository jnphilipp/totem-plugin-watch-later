TOTEM_PLUGINS_DIR?=~/.local/share/totem/plugins

ifdef VERBOSE
  Q :=
else
  Q := @
endif

install: watch_later.py watch_later.plugin config
	$(Q)install -Dm 0644 watch_later.py ${TOTEM_PLUGINS_DIR}/watch_later/watch_later.py
	$(Q)install -Dm 0644 watch_later.plugin ${TOTEM_PLUGINS_DIR}/watch_later/watch_later.plugin
	$(Q)install -Dm 0644 config ${TOTEM_PLUGINS_DIR}/watch_later/config

	@echo "watch later totem plugin install completed."
	@echo "Don't forget to activate it in totem."

uninstall:
	$(Q)rm -r "${TOTEM_PLUGINS_DIR}"/watch_later

	@echo "watch later totem plugin uninstall completed."
