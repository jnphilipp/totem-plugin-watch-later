# Watch later Totem Plugin
Totem video player plugin that starts a file at the time it stopped the last time it played. It also automatically continues to play the last file when Totem starts.

## Installation
Run `make install`, it will copy all necessary files in the plugin folder `~/.local/share/totem/plugins/watch_later`.

Alternately create the plugin folder in `~/.local/share/totem/plugins/watch_later`,
and copy the following files there:

* `watch_later.plugin`
* `watch_later.py`
* `config`

Then start Totem and enable "Watch later" plugin in the Plugins view.

## How it works
On playback, it stores the file path, the time and when it was created in a file in the plugin folder.

After opening the same file, its time will be restored.

If the `restart_last` feature is enabled (default), on Totem start it will wait 2 seconds (default), and then open the last played file and restores its time.

## Config
At the Moment it is only possible to configure the plugin via the `config` file in the plugin folder.

# If you will start a video before the delay, the auto load will be disabled.
* `restart_last`: play last video on start (true, false)
* `restart_delay`: delay before restart (seconds)
* `update_interval`: update interval for the video position (seconds)
* `rewind_time`: rewind from stopped time (seconds)
* `min_runtime`: only save the time after a minimum runtime (seconds)
* `max_runtime`: only save the time before a maximum runtime (seconds from the end)
