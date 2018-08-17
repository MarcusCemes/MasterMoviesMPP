# MasterMovies Media Processing Platform

[![Build](https://img.shields.io/travis/MarcusCemes/MasterMoviesMPP/master.svg?style=flat-square)](https://travis-ci.org/MarcusCemes/MasterMoviesMPP)
[![Downloads](https://img.shields.io/github/downloads/MarcusCemes/MasterMoviesMPP/total.svg?style=flat-square)](https://github.com/MarcusCemes/MasterMoviesMPP)
[![GitHub release](https://img.shields.io/github/release/MarcusCemes/MasterMoviesMPP.svg?style=flat-square)](https://github.com/MarcusCemes/MasterMoviesMPP/releases)
[![GitHub code size](https://img.shields.io/github/languages/code-size/MarcusCemes/MasterMoviesMPP.svg?style=flat-square)](https://github.com/MarcusCemes/MasterMoviesMPP)
[![License](https://img.shields.io/github/license/MarcusCemes/MasterMoviesMPP.svg?style=flat-square)](LICENSE.md)

A lightweight distributed video backend with Python sauce doing the magic. This goes well with [this](https://github.com/MarcusCemes/MasterMoviesMPP-interface)

![Image of the program](images/1.jpg)

## Getting Started

The *MasterMovies Media Processing Platform* is a backend video transcode engine, supercharged with the Python programming language.
It's a distributed node network, designed to work in a *Virtual Machine* or a *Docker*. With the only central point being the database server (which can also be mirrored to eliminate a single point of failure), jobs may be paused, resumed and even recovered in case a node crashes.
The transcode process is split into many segments, being all available to any node connected to the database, offering large scalability.

The system is designed as a video processing system for uploaded videos. It allows you to verify the integrity of the video container, and transcode it into multiple lower quality H.264 video files, ripe for dynamic variable-resolution streaming.

These instructions will get you a copy of the project up and running on your local machine for development and testing purposes. See deployment for notes on how to deploy the project on a live system.

### Prerequisites

*MasterMoviesMPP* is cross-platform, however it requires Python, FFmpeg and MySQL. This project is designed to run on Linux, but is completely compatible with Windows.
The following bash commands work on Ubuntu, and Ubuntu Server. You may need to adapt them to your Linux distribution.

In order to compile and run this program, you will need [Python 3](https://www.python.org/) and the bundled PyPi package manager. This is already installed on most Linux distributions.

```bash
$ sudo apt-get update
$ sudo apt-get install python3
```

[FFmpeg](https://ffmpeg.org/) is used to handle the video files. It needs to be either globally accessible from shell, or from the local installation directory.

```bash
$ sudo apt-get update
$ sudo apt-get install ffmpeg
```

At the heart of this software is the [MySQL](https://www.mysql.com/) (or [MariaDB](https://mariadb.org/)) database.

```bash
$ sudo apt-get update
$ sudo apt-get install mysql-server
$ sudo mysql_secure_installation  # This will allow you to create a root account.
```

### Installing

This section will guide you through the installation process, as well as setting up dependencies and the database.

Download or clone this repository onto your computer. The files you need to run the program are:

* MasterMoviesMPP Node.py  (this can be renamed)
* config.ini
* LICENSE.md

For the setup process, you will also need:
* MasterMoviesMPP.sql
* requirements.txt

#### Python Dependencies

To install dependencies from the *requirements.txt* file, run:
```bash
$ pip install -r requirements.txt
```
You may need to use sudo if you don't have write permissions, but this isn't [recommended](http://docs.python-guide.org/en/latest/dev/virtualenvs/)

On Linux, you may encounter an error when installing mysqlclient, "python setup.py egg_info failed with error code 1".
A way of fixing this is by running `$ apt install libmysqlclient-dev`

#### MySQL Database

You will need to set up a MySQL database, containing a specific database structure included in the *MasterMoviesMPP.sql* file. You may import this through tools such as PHPMyAdmin, or you can run the list of statements directly from the terminal.

The following steps will guide you through the steps required to open connections to the local network (localhost only by default), create a user for the node, and importing the database file.

To import the file from the terminal, create the database and append the .sql file:
```bash
$ mysql -u root -p -e "CREATE DATABASE MasterMoviesMPP;USE MasterMoviesMPP;" < MasterMoviesMPP.sql
```

To create a new user, you will need to use the *mysql* command to execute SQL statements.
```bash
$ mysql -u root -p
mysql> CREATE USER 'useername'@'192.168.%.%' IDENTIFIED BY 'password';
mysql> GRANT ALL PRIVILEGES ON MasterMoviesMPP.* TO 'username'@'192.168.%.%';
mysql> FLUSH PRIVILEGES;
mysql> exit
```

Lastly , if you plan on running nodes somewhere other than localhost, you will need to open the SQL server to the local network by editing the *my.cnf* (filename may vary), usually found somewhere like */etc/mysql/my.cnf* (this depends on your Linux distribution). Replace the line
```
bind-address = 127.0.0.1
# with:
#bind-address = 127.0.0.1
```

That's it! Restart the service with
```bash
sudo service mysql restart
```

Any references to 'tables' in this readme are references to tables that were imported to the database.


#### config.ini

Lastly, you will need to edit the *config.ini* file. Replace the database connection options with the ones you set up, and also the work directory with the path to the following folder structure somewhere on the computer or on the network:
* [work]  (name is configurable)
  * [source]  (name is configurable)
  * ingest
  * transcode
  * export
  * [delivery]  (optional, and name is configurable)

The source folder can be located elsewhere (if specified by the config.ini file).
Finished jobs will be available in the export folder. Processing a video file called video.mp4 with one 1080p60 output will make it available as:
[work]/export/*UUIDashex*/*video*1080p60.mp4 (see [UUIDs](#uuid-ecosystem))

Exported video files may also be copied to a delivery folder (again, by specification in the *config.ini* file). This makes them more easily available as (and allows the program purge the export work folders):
[delivery]/*video*1080p60.mp4

## Starting a node

To add a node to the system, run the python file from the command line with one of three node types as an argument:
```bash
$ python3 'MasterMoviesMPP Node.py' [ingest/transcode/export]
```
The program will attempt to create a connection to the database (see [setting up the database](#mysql-database)). Once a successful connection has been made, the node will register itself in the node table.

All further node operations are handled by the database. Nodes may be enabled, disabled and terminated by modifying its entry in the node table. To terminate the node, you may also stop the script using Ctrl+C on the terminal window *when the node is not working*. This will ensure that the program picks up the shutdown and exits safely, unregistering itself from the database.

### Adding a job

Adding a job to the queue is as simple as moving the file to the *[source]* directory and creating a row entry in the job table:
```sql
INSERT INTO job sourceName VALUES ( name )
```

Any authorised ingest node will pick up the job, starting the video ingest process into the system.
Transcode and Export nodes will pickup the job at the relevant stage, when the ingest is complete.
Once the job is complete, the *isComplete* column of the job row will be set to 1 (after the file has been moved to the appropriate directory)

Completed or failed jobs will be reported as a failure on the database, and the work folders will be purged. Upon failure, the source video file is moved to [work]/quarantine/, and upon completion it is deleted altogether.

#### Outputs

To add/modify outputs, you will need to change the *output* table. Each row corresponds to one encode output.
 * active - Whether the output should be processed
 * maxY - The maximum vertical resolution of the encode
 * maxX - The maximum horizontal resolution of the encode
 * CRF - The Constant Rate Factor quality setting (relates to the bitrate, default: 23, see FFmpeg documentation)
 * preset - The encoding preset (default: main)
 * profile - The encoding profile, better quality per file size at a cost of encoding time (default: medium)
 * maxFramerate - The framerate cap to be applied to the encode
 * audioBitrate - The audio bitrate in kb/s (codec is AAC, all audio streams are re-encoded)

The output resolution will be resized to fit in the (maxX)x(maxY) frame, conserving the aspect ratio. Outputs that would upscale will be ignored. If all outputs would upscale, the smallest maxY output will be chosen.

The maxY is also used for file naming, giving outputs names with the likes of (sourceName)(maxY)p(maxFramerate).mp4

### Monitoring the system

The database is the central control panel. It allows you to control each node individually, as well as modify the [global policies](#database-policies) controlling all nodes.

To provide a GUI interface for the database control system, there is a [HTML Interface](https://github.com/MarcusCemes/MasterMoviesMPP-interface) in development, that gives you an easy way to control nodes, policies and the addition/deletion of jobs. The login credentials are stored in the interface table. The passwords are hashed using the PHP password_hash function. The default login is: 'admin', 'password'.

You are free to create your own interface, the available database columns that offer control are:
* MasterMoviesMPP.policy.value
* MasterMoviesMPP.node.authorise
* MasterMoviesMPP.node.terminate
* MasterMoviesMPP.output.*  (Each row is an output that will be encoded)

## Deployment

To have a fully working system, you must have at least one of each node running (ingest, transcode, export). In future releases, these nodes should be merged into one configurable node.

All communication with the system should be done through the database. Filesystem event triggers should not be relied on, as the output may not have finished encoding, or may have failed and is being rolled back to a previous state. These events may be useful, however, as a trigger to check the status with the database.

The nodes can run across any network, as long as the database and work folder is accessible. There should only be one work folder for the entire system, as each node uses it for read and write operations, and file communication. They should not be accessible externally, as this is a server backend system. Any nodes that failed to unregister will be purged from the database after a certain period of inactivity (see [Database Policies](#database-policies)). Any node that was removed from the node table, which is still active, will terminate securely.

It is possible that nodes could conflict by overwriting each other. Although this is theoretically impossible, mistakes happen, especially if the node is waiting on a FFmpeg operation and while its entry and assigned job are being manipulated on the database.

Removing a job prematurely will not result in a purge of work folders, this would require manual cleaning. A safe way would be to deactivate ingest, finish all jobs, then clean all of the work directories.

### How it works

#### Ingest

When a row is added with a status of 0 to the job table, an ingest node will pick it up. If the policy is active, it will verify the integrity of the video file, before splitting it into many segments by key frames. The job will then be updated to a status of 2, and relevant job openings created in the transcodeJob table.

#### Transcode

Transcode nodes will pick up an available transcode segment if a job is in the transcode stage. It will transcode that segment into all of active [outputs](#outputs).
After each transcode completion, it will check to see whether all transcodes are complete, in which case the job status will be upgraded to a status of 3

#### Export

Export nodes will actively search for transcoded jobs. When one is assigned, they will verify the presence of all transcoded file segments, rolling back and restarting the failed transcode jobs if necessary. If all are present, it will begin exporting each resolution, by fusing the all the video segments, while encoding the audio stream from the source file. The fused video stream and the newly encoded audio stream are output into the same video container, ready for delivery.

#### Database Policies

Database policies allow you to apply global settings to each node. The following policies are availiable:

 * **ingestEnabled** - Authorises ingest nodes
 * **transcodeEnabled** - Authorises transcode nodes
 * **exportEnabled** - Authorises export nodes
 * **terminateAll** - Force all nodes to exit safely
 * **nodeTimeout** - The time in seconds, after which nodes will be purged from the node table after no activity.
 * **verifyDuringIngest** - Whether the video integrity should be verified during ingest (requires decoding the entire video file)
 * **failureTolerance** - The amount of times a task can fail before the job is marked as a failure

#### UUID Ecosystem

Each node and job is given a unique identifier, conform with [RFC 4122](https://tools.ietf.org/html/rfc4122). This UUID is used instead of the primary key when referencing jobs, tables and nodes. The 128-bit number is used in its 32 character hex-form when naming job folders, and stored as a 16-byte value in the database.

When a new UUID is generated, the database is double-checked for duplicates, despite the ridiculous low chance of conflicts.

## Built With

* [Python 3](https://www.python.org/) - Python 3 Compile and Runtime Environment
* [PyPi](https://pypi.python.org/pypi) - Python Dependency Management (see [Prerequisites](#prerequisites))
* [FFmpeg](https://ffmpeg.org/) - Used to transcode video
* [MySQL](https://www.mysql.com/) - Keep track of jobs, and inter-node communication.

## Versioning

We use a relaxed form of [SemVer](http://semver.org/) for versioning. For the versions available, see the [tags on this repository](https://github.com/MarcusCemes/MasterMoviesMPP/tags).

## Authors

* **Marcus Cemes** - *Founder & Project Leader* - [MarcusCemes](https://github.com/MarcusCemes)

This is a young project, started in January 2018. If you have any ideas, or would like to contribute, make a fork or hit the issues discussions.

## License

This project is licensed under the GPL-3.0 License - see the [LICENSE.md](LICENSE.md) file for details

*TL;DR* You may distribute, modify and use this software for private and commercial purposes, under the condition of preserving the license and copyright status. **Don't steal this.**

## Acknowledgments

* Thanks to [TurboThread](http://www.turbothread.com) for kick-starting this project
