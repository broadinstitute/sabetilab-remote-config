### Windows ExpanDrive mount

#### Background and Usage

In order to monitor samba directories (for example, via the  [Sequencing Analysis Viewer](http://support.illumina.com/sequencing/sequencing_software/sequencing_analysis_viewer_sav.html)), it is necessary to mount remote field machines as local drives. On Windows this can be performed via ExpanDrive, a maintained commercial Windows alternative to sshfs. The remote mounts are complicated by the dynamic and relayed nature of the field deployment SSH configuration. Connections must be made with the relay host rather than directly with field machines. 

It is possible to mount remote MiSeq run folders on Windows via ExpanDrive. A helper script (in exe form via [py2exe](http://www.py2exe.org/)) takes care of updating the dynamic ports used by the field nodes, based on a read-only AWS IAM account with access to the resource records for a particular hosted zone.

The following assumptions are made:

* Windows 10
* [ExpanDrive](http://www.expandrive.com/apps/expandrive/) v5.1.9
* An install of VisualStudio, Python, or another source of MSVCR90.dll as required by py2exe executables (see: http://www.py2exe.org/index.cgi/Tutorial#Step52)
* Running copy of [Pageant](http://www.chiark.greenend.org.uk/~sgtatham/putty/download.html) to manage SSH keys (and PuTTYgen)

Setup steps are as follows:

Create an SSH key pair for the user who will be accessing the remote systems

Add the public key to the user's GitHub account

Add the GitHub username to the settings_manager.yml and settings_field_node.yml files.

Run the `field-node/node-users.yml` and `field-node/node-samba.yml`  playbooks (in that order) to set permissions and group memberships .

Install ExpanDrive. Reboot if prompted.

On the user's Windows machine, convert the private key to PuTTY format, if necessary, start Pageant and add the private key. Keep PuTTY running.

Run the helper executable to update the ExpanDrive config with current field hostnames and ports. By default ExpanDrive will prompt for a username each time unless one is provided in the settings for a particular server.

Connect to a particular field machine in ExpanDrive to mount it as a drive.

#### Building instructions

In order to build the helper program under Python 3.4, the following packages are needed. All can be installed via `pip`:
* psutil
* PyYAML
* boto==2.39.0
* python-dateutil

The `*.exe` file can be built via:
`python setup.py py2exe`
