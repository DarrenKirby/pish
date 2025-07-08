### pish - the python idiot shell

Similar to bash, but without the shell scripting parts (yet).

* Requires Python 3.6 or better.
* Requires `prompt toolkit` library: https://python-prompt-toolkit.readthedocs.io/en/master/#
* Requires `Pygments` library: https://pygments.org/

You can run `make` or `pip install -r requirements.txt` to install the requirements.

To run the shell, just type `python3 src/pish.py`. The shell will start with `$HOME` as your `$PWD`.

Implemented so far:

* `echo $HOME` will output value of envvars, `echo $?` is last exit status, `echo ??` is pid of shell.
* arbitrary piped commands work ie: `cat foo.txt | sort | uniq`
* arbitrary `&&` commands work ie: `./configure && make && make install`
* arbitrary `||` commands work ie: `mount-l || cat /etc/mtab || cat /proc/mounts`
* STDOUT redirection works ie: `df -h > df.txt` or `ifconfig >> netlog.txt`
* `histsize` history buffer that is read/written to `histfile`.
* Preface sensitive commands with a space to prevent writing to the history buffer.
* rudimentary tab completion. Only works in PWD so far...
* Customizable prompts, though this is currently crufty.
* `~/.pishrc` configuration file for prompt/prompt style, HISTFILE and HISTSIZE.
* Shell globbing: works as expected with `*`, `?`, `[abc]`, `[a-z]`, `{1,2,3}` and `{5..1}`.

My eventual plan is to wrap this with `prompt_toolkit` and make it a full-screen term app so it does
not need to run or be started fromm another shell.

Released under the GPL-3 license.
