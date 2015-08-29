#!/bin/sh

cp ../splitcpy*deb deb/

cd deb
echo MD5Sum >checksums.txt
md5sum *deb >>checksums.txt
echo >>checksums.txt
echo "SHA1" >>checksums.txt
sha1sum *deb >>checksums.txt
echo >>checksums.txt
echo "SHA256" >>checksums.txt
sha256sum *deb >>checksums.txt
echo  >>checksums.txt

gpg --clearsign checksums.txt
rm checksums.txt
mv checksums.txt.asc checksums.txt

cd ..

./mkjson

cd man
./makeman
cd ..

cd repo
./clearit
./addit
cd ..



