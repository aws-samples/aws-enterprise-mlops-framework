#!/bin/bash
CONFIG_FILE=$1
GDK_ARTEFACTS_DIR=$2
ROOT=""
NAME=""

cd $GDK_ARTEFACTS_DIR
unzip publish.zip
echo "switching folder to $GDK_ARTEFACTS_DIR/publish .."
cd publish

WORKDIR=$(pwd)

echo "Parsing components .."
while read -r line; do
    if [[ $line == root:* ]]; then
        echo $line
        ROOT=$(echo $line | sed 's/root://' | sed 's/ //' | tr -d '\"')
    elif [[ $line == component-name:* ]]; then
        echo $line
        NAME=$(echo $line | sed 's/component-name://' | sed 's/ //' | tr -d '\"')
    fi

    if [[ ! -z "$ROOT" ]] && [[ ! -z "$NAME" ]]; then

        echo "switching folder to $ROOT .."
        cd $WORKDIR/$ROOT

        echo "Publishing $NAME component .."
        gdk component publish
        echo "Done."

        ROOT=""
        NAME=""
    fi

done < $CONFIG_FILE

cd $WORKDIR
