import argparse
import gzip
import modelib as ml
import csv

parser = argparse.ArgumentParser(
	description='Generates len, MM, and PWM models for apc')

parser.add_argument('--extxt', type=str, metavar='<file>', 
	required=False, help='input text file with exon sequences')
parser.add_argument('--intxt', type=str, metavar='<file>',
	help='input text file with intron sequences')
parser.add_argument('--dntxt', type=str, metavar='<file>',
	help='input text file with donor site sequences')
parser.add_argument('--actxt', type=str, metavar='<file>',
	help='input text file with acceptor site sequences')
parser.add_argument('-mm', action='store_true')
parser.add_argument('-len', action='store_true')
parser.add_argument('-pwm', action='store_true')

args = parser.parse_args()

exons = ml.read_txt_seqs(args.extxt)

exinlen_yscores, exinlen_yvalues = ml.memoize_fdist(exons, pre2=6)

print(exinlen_yscores)
print(exinlen_yvalues)

with open('lenmod.csv', 'w', newline='') as tsvfile:
	writer = csv.writer(tsvfile, delimiter=',', lineterminator='\n')
	for i in range(len(exinlen_yscores)):
		writer.writerow([exinlen_yvalues[i], exinlen_yscores[i]])
tsvfile.close()

def mm_tsv_write(exins, fp):

	exinmm_scores, exinmm_probs = ml.make_mm(exins)

	root, ext = fp.split('.')
	filename = root + '_mm' + '.tsv'

	with open(filename, 'w', newline='') as tsvfile:
		writer = csv.writer(tsvfile, delimiter='\t', lineterminator='\n')
		for key in exinmm_scores:
			writer.writerow([key + 'A', exinmm_probs[key][0], 
				exinmm_scores[key][0]])
			writer.writerow([key + 'C', exinmm_probs[key][1], 
				exinmm_scores[key][1]])
			writer.writerow([key + 'G', exinmm_probs[key][2], 
				exinmm_scores[key][2]])
			writer.writerow([key + 'T', exinmm_probs[key][3], 
				exinmm_scores[key][3]])
	tsvfile.close()


'''
if args.extxt and args.mm:
	exons = ml.read_txt_seqs(args.extxt)
	mm_tsv_write(exons, args.extxt)
elif args.extxt and args.len:
	# len_tsv_write(exons)
	exons = ml.read_txt_seqs(args.extxt)	
elif args.extxt:
	exons = ml.read_txt_seqs(args.extxt)
	# len_tsv_write(exons)
	mm_tsv_write(exons, args.extxt)
							
if args.intxt and args.mm:
	introns = ml.read_txt_seqs(args.intxt)
	mm_tsv_write(introns, args.intxt)
elif args.intxt and args.len:
	introns = ml.read_txt_seqs(args.intxt)
	# len_tsv_write(introns)
elif args.intxt:
	introns = ml.read_txt_seqs(args.intxt)
	# len_tsv_write(introns)
	mm_tsv_write(introns, args.intxt)
'''












