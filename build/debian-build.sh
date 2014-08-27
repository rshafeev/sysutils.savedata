#!/usr/bin/bash
# copy files to deb-build path

# полный путь до скрипта
ABSOLUTE_FILENAME=`readlink -e "$0"`
# каталог в котором лежит скрипт
DIRECTORY=`dirname "$ABSOLUTE_FILENAME"`

echo $DIRECTORY

# clear
VERSION="0.01~beta"
PACKAGE="savedata_${VERSION}_all.deb"
cd deb-build
rm -r usr
rm -r var
rm -r etc
cd ..

# create dirs
mkdir deb-build/usr/
mkdir deb-build/usr/lib
mkdir deb-build/usr/lib/savedata

mkdir deb-build/etc
mkdir deb-build/etc/savedata

# copy files
echo "copy file ..."
cp -r ../savedata-backup/*.py deb-build/usr/lib/savedata
cp -r ../savedata-backup/*.json deb-build/usr/lib/savedata
cp -r ../savedata-backup/*.sh deb-build/usr/lib/savedata
cp -r ../conf/* deb-build/etc/savedata/

# change permissions
echo "path: $DIRECTORY"
chmod 0755 -R "$DIRECTORY/deb-build"
chmod 0644 "$DIRECTORY/deb-build/DEBIAN/control"

fakeroot dpkg-deb --build deb-build

mv deb-build.deb $PACKAGE

lintian $PACKAGE

echo "finish."
