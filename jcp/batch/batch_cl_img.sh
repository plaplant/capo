#$ -S /bin/bash
#$ -V
#$ -j y
#$ -cwd
#$ -o grid_output/

FILES=`pull_args.py $*`
echo "cl_img.py -d cln -r radial ${FILES}"
cl_img.py -d cln -r radial ${FILES} --maxiter=10000 --div --tol=1e-6
#C1=15
#C2=185
#dC=5
#CHS=`python -c "for a in range($C1,$C2,$dC): print '%d_%d' % (a,a+5)"`
#MYCHS=`pull_args.py $CHS`
#for ch in $MYCHS ; do
#    echo Working on channels: $ch
#    FMT_FILE=pgb966_c${ch}_
#    cl_img.py -d cln --maxiter=10000 ${FMT_FILE}*.d[ib]m.fits
#done
