'''
import argparse

parser = argparse.ArgumentParser()
parser.add_argument('fasta', type=str, metavar='<file>',
	help='wormbase fasta file for one gene')
parser.add_argument('wb_gff', type=str, metavar='<file>',
	help='wormbase nnotation gff file')
parser.add_argument('apcgen_gff', type=str, metavar='<file>',
	help='apc generated gff file')

args = parser.parse_args()
'''
def get_seq(fasta):

	with open(fasta, 'r') as fp:
		seq = ''
		for line in fp.readlines():
			line = line.rstrip()
			if line.startswith('>'):
				gID = line
			else:
				seq += line

	return seq	
	
def get_wbgene_info(wb_gff, seq):
	
	wbginfo = {}
	with open(wb_gff, 'r') as fp:
		wbg = {}
		wbg['mRNA'] = []
		wbg['exons'] = []
		wbg['introns'] = []
		for line in fp.readlines():
			line = line.rstrip()
			sline = line.split('\t')
			if sline[2] == 'mRNA':
				name = sline[0]+'-wb'
				wbg['mRNA'] = [int(sline[3]), int(sline[4])]
				WBGene = sline[8].split(':')[2]
				wbg['Parent=Gene'] = WBGene
			if sline[2] == 'CDS':
				wbg['exons'].append((int(sline[3]), int(sline[4])))
			if sline[1] == 'WormBase' and sline[2] == 'intron':
				wbg['introns'].append((int(sline[3]), int(sline[4])))
		wbginfo[name] = wbg
		
	for gID in wbginfo:
		for ft in wbginfo[gID]:
			if ft == 'exons':
				wbginfo[gID][ft] = sorted(wbginfo[gID][ft]) 

	return wbginfo

def check_CDS(info):

	ntsum = 0
	for gID in info:	
		ntsum = 0
		for ex in info[gID]['exons']:
			ntsum += ex[1] - ex[0] + 1
		if ntsum%3 == 0:
			info[gID]['in_frame'] = True
		else:
			info[gID]['in_frame'] = False
	
	return info

def get_start_stop(wbginfo):
	
	for gn in wbginfo:
		clist = []
		wbstart = wbginfo[gn]['exons'][0][0]	
		wbstop = wbginfo[gn]['exons'][-1][1]

	return wbstart, wbstop	
	
def get_apcgen_info(apcgen_gff, wbstart, wbstop):

	apc_isos = {}
	with open(apcgen_gff, 'r') as fp:
		icount = 0
		gID = ''
		for line in fp.readlines():
			line = line.rstrip()
			if 'name' in line:
				gID = line.split(' ')[2]
			sline = line.split('\t')
			if len(sline) < 9: continue
			if sline[2] == 'gene': continue
			if sline[2] == 'mRNA':
				icount += 1
				apc_isos[f'{gID}-{icount}'] = [sline]
			if sline[2] == 'exon':
				apc_isos[f'{gID}-{icount}'] += [sline]
			if sline[2] == 'intron':
				apc_isos[f'{gID}-{icount}'] += [sline]
	
	apcgen_isos = {}	
	for iso in apc_isos:
		apcgen_isos[iso] = {}
		mRNA = []
		prob = float
		escores = []
		iscores = []
		efreqs = []
		ifreqs = []
		exons = []
		introns = []
		for ft in apc_isos[iso]:
			if ft[2] == 'mRNA':
				mRNA.append(ft[3])
				mRNA.append(ft[4])
				prob = float(ft[5])
			if ft[2] == 'exon':
				exons.append((int(ft[3]), int(ft[4])))
				escore = ft[8].split(';')[1]
				escore = float(escore.split('=')[1])
				escores.append(escore)
			if ft[2] == 'intron':
				introns.append((int(ft[3]), int(ft[4])))
				iscore = ft[8].split(';')[1]
				iscore = float(iscore.split('=')[1])
				iscores.append(iscore)
		exons2 = []
		first = (wbstart, exons[0][1])
		exons2.append(first)
		for ex in exons:
			if ex == exons[0]: continue
			if ex == exons[-1]: continue
			exons2.append(ex)
		last = (exons[-1][0], wbstop)
		exons2.append(last)
		apcgen_isos[iso]['mRNA'] = mRNA
		apcgen_isos[iso]['prob'] = prob
		apcgen_isos[iso]['exons'] = exons2
		apcgen_isos[iso]['escores'] = escores
		apcgen_isos[iso]['introns'] = introns
		apcgen_isos[iso]['iscores'] = iscores

	return apcgen_isos

def check_exon_count(apcgen_isos, wbg_info):

	for iso in apcgen_isos:
		gID = iso.split('-')[0] + '-wb'
		wb_enum = len(wbg_info[gID]['exons'])
		apc_enum = len(apcgen_isos[iso]['exons'])
		apcgen_isos[iso]['dif_exon'] = apc_enum - wb_enum 

	return apcgen_isos

def check_wb_frame(apcgen_isos, wbg_info):

	for iso in apcgen_isos:
		if apcgen_isos[iso]['dif_exon'] != 0:
			apcgen_isos[iso]['wb_frame'] = False
		if apcgen_isos[iso]['dif_exon'] == 0:
			gID = iso.split('-')[0] + '-wb'
			wb_ex = wbg_info[gID]['exons']
			apc_ex = apcgen_isos[iso]['exons']
			if wb_ex == apc_ex: 
				apcgen_isos[iso]['wb_frame'] = True
			else:
				apcgen_isos[iso]['wb_frame'] = False
	
	return apcgen_isos

def get_codons(apcgen_isos, seq):

	for iso in apcgen_isos:
		codons = []
		for ex in apcgen_isos[iso]['exons']:
			first = seq[ex[0]-1:ex[0]+2]
			last = seq[ex[1]-3:ex[1]]
			codons.append([first, last])
		apcgen_isos[iso]['codons'] = codons
	
	return apcgen_isos

def find_PTCs(apcgen_isos, seq):

	for iso in apcgen_isos:
		if apcgen_isos[iso]['wb_frame'] == False:
			CDS = ''
			for ex in apcgen_isos[iso]['exons']:
				eseq = seq[ex[0]-1:ex[1]]
				CDS += eseq
			shift = 0
			PTCs = []
			for i in range(len(CDS)):
				codon = CDS[i+shift:i+shift+3]
				if len(codon) == 3: 
					if codon in ['TAG', 'TAA', 'TGA']:
						PTCs.append((i+shift+1, codon))	
				shift += 2
			if len(PTCs) > 0:
				apcgen_isos[iso]['PTC'] = PTCs
			else:
				apcgen_isos[iso]['PTC'] = False
		else:
			apcgen_isos[iso]['PTC'] = False
		
	return apcgen_isos	

def amass_info(fasta, wb_gff, apcgen_gff):

	seq = get_seq(fasta)
	wbg_info = get_wbgene_info(wb_gff, seq)
	wbg_info = check_CDS(wbg_info)
	wbg_info = get_codons(wbg_info, seq) #####
	wbstart, wbstop = get_start_stop(wbg_info)
	apcgen_isos = get_apcgen_info(apcgen_gff, wbstart, wbstop)
	apcgen_isos = check_CDS(apcgen_isos)
	apcgen_isos = check_exon_count(apcgen_isos, wbg_info)
	apcgen_isos = check_wb_frame(apcgen_isos, wbg_info)
	apcgen_isos = get_codons(apcgen_isos, seq)
	apcgen_isos = find_PTCs(apcgen_isos, seq)
	apcgen_isos.update(wbg_info)

	return apcgen_isos
'''
apcgen_isos = amass_info(args.fasta, args.wb_gff, args.apcgen_gff)

for i in apcgen_isos:
	print(i, apcgen_isos[i])
'''
# ch.4738 has a short first exon 
# all wb genes have at least 1 intron
# but will APC generate isos with no introns?
# ch.11934 has 3 CDS, ordered last to first
# ch.216 has 2 CDS
# ch.4738 has 4 CDS 
# ch.4741, 2nd isoform is given an extra exon/intron
# ch.241 has 3 CDS, 2nd isoform has correct firt and last exons
# but middle exon is cut out as an intron, then goes out of frame
