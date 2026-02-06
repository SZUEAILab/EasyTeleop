#!/bin/sh

export LD_LIBRARY_PATH=./:$LD_LIBRARY_PATH
export LD_LIBRARY_PATH=./sdk_lib:$LD_LIBRARY_PATH
export LD_LIBRARY_PATH=./sdk_lib/ffmpeg3:$LD_LIBRARY_PATH


while :
do
	echo "Current DIR is " $PWD
	stillRunning=$(ps -ef |grep "$PWD/trro-test" |grep -v "grep")
	if [ "$stillRunning" ] ; then
		echo "TRRO service was already started by another way"
		echo "Kill it and then startup by this shell, other wise this shell will loop out this message annoyingly"
		killall $PWD/trro-test

	else
		echo "TRRO service was not started"
		echo "Starting service ..."
		$PWD/trro-test
		echo "TRRO service was exited!"
	fi
	sleep 3
done
