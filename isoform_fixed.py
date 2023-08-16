import copy
import gzip
import itertools
import math
import random
import sys

#####################
## UTILITY SECTION ##
#####################

def randseq(n):
	seq = ''
	for i in range(n):
		seq += random.choice('ACGT')
	return seq

def get_filepointer(filename):
	fp = None
	if   filename.endswith('.gz'): fp = gzip.open(filename, 'rt')
	elif filename == '-':          fp = sys.stdin
	else:                          fp = open(filename)
	return fp

def read_fasta(filename):

	name = None
	seqs = []

	fp = get_filepointer(filename)

	for line in fp.readlines():
		line = line.rstrip()
		if line.startswith('>'):
			if len(seqs) > 0:
				seq = ''.join(seqs)
				yield(name, seq)
				name = line[1:]
				seqs = []
			else:
				name = line[1:]
		else:
			seqs.append(line)
	yield(name, ''.join(seqs))
	fp.close()

def prob2score(p):
	if p == 0: return -100
	return math.log2(p/0.25)

def entropy(ps):
	assert(math.isclose(sum(ps), 1))
	h = 0
	for p in ps:
		h -= p * math.log2(p)
	return h

def kld(p, q):
	assert(math.isclose(sum(p), 1.0))
	assert(math.isclose(sum(q), 1.0))
	d = 0
	for pi, qi in zip(p, q):
		d += pi * math.log2(pi / qi)
	return d

def manhattan(p, q):
	assert(math.isclose(sum(p), 1.0, abs_tol=1e-6))
	assert(math.isclose(sum(q), 1.0, abs_tol=1e-6))
	d = 0
	for pi, qi in zip(p, q):
		d += abs(pi - qi)
	return d

#################
## PWM SECTION ##
#################

def create_pwm(seqs):
	count = []
	for seq in seqs:
		for i, nt in enumerate(seq):
			if len(count) <= i:
				count.append({'A':0, 'C': 0, 'G': 0, 'T': 0})
			count[i][nt] += 1

	pwm = [{} for i in range(len(count))]
	for i in range(len(count)):
		for nt in count[i]:
			pwm[i][nt] = count[i][nt] / len(seqs)
	return pwm

def write_pwm(file, pwm):
	with open(file, 'w') as fp:
		fp.write(f'% PWM {file} {len(pwm)}\n')
		for pos in pwm:
			for nt in pos:
				fp.write(f'{pos[nt]:.6f} ')
			fp.write('\n')

def read_pwm(file):
	nts = ('A', 'C', 'G', 'T')
	pwm = []

	# read raw values
	with open(file) as fp:
		for line in fp.readlines():
			if line.startswith('%'): continue
			f = line.split()
			d = {}
			for nt, val in zip(nts, f):
				d[nt] = float(val)
			pwm.append(d)

	# convert to log-odds
	for i in range(len(pwm)):
		for nt in nts:
			pwm[i][nt] = prob2score(pwm[i][nt])

	return pwm

def score_pwm(pwm, seq, pos):
	score = 0
	for i in range(len(pwm)):
		nt = seq[pos+i]
		score += pwm[i][nt]
	return score

####################
## LENGTH SECTION ##
####################

def create_len(seqs, floor, limit):
	count = []
	sum = 0
	icount = 0
	for seq in seqs:
		n = len(seq)
		sum += n
		icount += 1
		while len(count) < n+1 :
			count.append(0)

		count[n] += 1

	# rectangular smoothing
	r = 5 # 5 on each side
	smooth = [0 for i in range(len(count))]
	for i in range(r, len(count) -r):
		for j in range(-r, r+1):
			smooth[i+j] += count[i]

	for i in range(floor):
		smooth[i] = 0
	smooth = smooth[:limit]

	# model
	model = []
	total = 0
	for v in smooth: total += v
	for v in smooth: model.append(v/total)

	return model

def write_len(file, hist):
	with open(file, 'w') as fp:
		fp.write(f'% LEN {file} {len(hist)}\n')
		for val in hist:
			fp.write(f'{val:.6f}\n')

def find_tail(val, x):
	lo = 0
	hi = 1000

	while hi - lo > 1:
		m = (hi + lo) / 2;
		p = 1 / m
		f = (1 - p)**(x-1) * p
		if f < val: lo += (m - lo) / 2
		else:       hi -= (hi - m) / 2

	return m

def read_len(file):
	model = []
	with open(file) as fp:
		for line in fp.readlines():
			if line.startswith('%'): continue
			line = line.rstrip()
			model.append(float(line))
	#print(model[-1])
	size = len(model)
	tail = find_tail(model[-1], size)
	expect = 1 / size;
	for i in range(len(model)):
		if model[i] == 0: model[i] = -100
		else:             model[i] = math.log2(model[i] / expect)

	return {'tail': tail, 'size':len(model), 'val': model}

def score_len(model, x):
	assert(x > 0)
	if x >= model['size']:
		p = 1 / model['tail']
		q = (1-p)**(x-1) * p
		expect = 1 / model['size']
		s = math.log2(q/expect)
		return s
	else:
		return model['val'][x]

##########################
## MARKOV MODEL SECTION ##
##########################

def create_markov(seqs, order, beg, end):
	count = {}
	for seq in seqs:
		for i in range(beg+order, len(seq) - end):
			ctx = seq[i-order:i]
			nt = seq[i]
			if ctx not in count: count[ctx] = {'A':0, 'C':0, 'G':0, 'T':0}
			count[ctx][nt] += 1

	# these need to be probabilities
	mm = {}
	for kmer in count:
		mm[kmer] = {}
		total = 0
		for nt in count[kmer]: total += count[kmer][nt]
		for nt in count[kmer]: mm[kmer][nt] = count[kmer][nt] / total

	return mm

def write_markov(file, mm):
	with open(file, 'w') as fp:
		fp.write(f'% MM {file} {len(mm)*4}\n')
		for kmer in sorted(mm):
			for v in mm[kmer]:
				fp.write(f'{kmer}{v} {mm[kmer][v]:.6f}\n')
			fp.write('\n')

def read_markov(file):
	mm = {}
	k = None
	with open(file) as fp:
		for line in fp.readlines():
			if line.startswith('%'): continue
			f = line.split()
			if len(f) == 2:
				mm[f[0]] = prob2score(float(f[1]))
				if k == None: k = len(f[0])
	return {'k': k, 'mm': mm}

def score_markov(model, seq, beg, end):
	score = 0
	k = model['k']
	mm = model['mm']

	for i in range(beg, end -k + 2):
		kmer = seq[i:i+k]
		score += mm[kmer]

	return score

################################
## TRANSCRIPT SCORING SECTION ##
################################

def score_apwm(pwm, tx):
	score = 0
	for intron in tx['introns']:
		score += score_pwm(pwm, tx['seq'], intron[1] - len(pwm) +1)
	return score

def score_dpwm(pwm, tx):
	score = 0
	for intron in tx['introns']:
		score += score_pwm(pwm, tx['seq'], intron[0])
	return score

def score_elen(model, tx):
	score = 0
	for exon in tx['exons']:
		score += score_len(model, exon[1] - exon[0] + 1)
	return score

def score_ilen(model, tx):
	score = 0
	for intron in tx['introns']:
		score += score_len(model, intron[1] - intron[0] + 1)
	return score

def score_emm(mm, tx):
	score = 0
	for exon in tx['exons']:
		score += score_markov(mm, tx['seq'], exon[0], exon[1])
	return score

def score_imm(mm, tx, dpwm, apwm):
	score = 0
	for intron in tx['introns']:
		#print(len(dpwm), len(apwm), 'HERE')
		beg = intron[0] + len(dpwm)
		end = intron[1] - len(apwm)
		score += score_markov(mm, tx['seq'], beg, end)
	return score

################################
## ISOFORM GENERATION SECTION ##
################################

def short_intron(dons, accs, min):
	for d, a in zip(dons, accs):
		intron_length = a - d + 1
		if intron_length < min: return True
	return False

def short_exon(dons, accs, seqlen, flank, min):

	# first exon
	# indexing bug was here
	exon_beg = flank #+ 1
	#print(exon_beg)
	exon_end = dons[0] -1
	exon_len = exon_end - exon_beg + 1
	if exon_len < min: return True

	# last exon
	exon_beg = accs[-1] + 1
	exon_end = seqlen - flank + 1
	exon_len = exon_end - exon_beg + 1
	if exon_len < min: return True

	# interior exons
	for i in range(1, len(dons)):
		exon_beg = accs[i-1] + 1
		exon_end = dons[i] - 1
		exon_len = exon_end - exon_beg
		if exon_len < min: return True
	return False

def gtag_sites(seq, flank, minex):
	dons = []
	accs = []
	for i in range(flank + minex, len(seq) -flank -minex):
		if seq[i:i+2]   == 'GT': dons.append(i)
		if seq[i-1:i+1] == 'AG': accs.append(i)
	return dons, accs

def gff_sites(seq, gff, gtag=True):
	dond = {}
	accd = {}
	with open(gff) as fp:
		for line in fp.readlines():
			if line.startswith('#'): continue
			f = line.split()
			if len(f) < 8: continue
			if f[2] != 'intron': continue
			if f[6] != '+': continue
			beg = int(f[3]) -1
			end = int(f[4]) -1
			if gtag:
				if seq[beg:beg+2]   != 'GT': continue
				if seq[end-1:end+1] != 'AG': continue
			dond[beg] = True
			accd[end] = True

	dons = list(dond.keys())
	accs = list(accd.keys())
	dons.sort()
	accs.sort()

	return dons, accs

def build_mRNA(seq, beg, end, dons, accs):
	assert(beg <= end)
	assert(len(dons) == len(accs))

	tx = {
		'seq': seq,
		'beg': beg,
		'end': end,
		'exons': [],
		'introns': [],
		'score': 0
	}

	if len(dons) == 0:
		tx['exons'].append((beg, end))
		return tx

	# introns
	for a, b in zip(dons, accs):
		tx['introns'].append((a, b))

	# exons
	tx['exons'].append((beg, dons[0] -1))
	for i in range(1, len(dons)):
		a = accs[i-1] + 1
		b = dons[i] -1
		tx['exons'].append((a, b))
	tx['exons'].append((accs[-1] +1, end))

	return tx

def all_possible(seq, minin, minex, maxs, flank, gff=None):

	if gff: dons, accs = gff_sites(seq, gff)
	else:   dons, accs = gtag_sites(seq, flank, minex)

	info = {
		'trials' : 0,
		'donors': len(dons),
		'acceptors': len(accs),
		'short_intron': 0,
		'short_exon': 0,
	}

	isoforms = []
	sites = min(len(dons), len(accs), maxs)
	for n in range(1, sites+1):
		for dsites in itertools.combinations(dons, n):
			for asites in itertools.combinations(accs, n):
				info['trials'] += 1

				# sanity checks
				if short_intron(dsites, asites, minin):
					info['short_intron'] += 1
					continue

				if short_exon(dsites, asites, len(seq), flank, minex):
					info['short_exon'] += 1
					continue

				# create isoform and save
				tx = build_mRNA(seq, flank, len(seq) -flank -1, dsites, asites)
				isoforms.append(tx)

	return isoforms, info

########################
## EXPRESSION SECTION ##
########################

def complexity(txs):
	prob = []
	total = 0
	for tx in txs:
		w = 2 ** tx['score']
		prob.append(w)
		total += w
	for i in range(len(prob)):
		prob[i] /= total
	return entropy(prob)

def get_introns(gff):
	introns = {}
	total = 0
	with open(gff) as fp:
		for line in fp.readlines():
			if line.startswith('#'): continue
			f = line.split()
			if len(f) < 8: continue
			if f[2] != 'intron': continue
			if f[6] != '+': continue
			beg, end, score = f[3], f[4], f[5]
			beg = int(beg)
			end = int(end)
			score = 0 if score == '.' else float(score)
			if (beg,end) not in introns: introns[(beg,end)] = 0
			introns[(beg,end)] += score
			total += score

	# convert to histogram
	for k in introns: introns[k] /= total

	return introns

def expdiff(introns1, introns2):

	# non-mutating
	i1 = copy.deepcopy(introns1)
	i2 = copy.deepcopy(introns2)

	# ensure all introns are in both collections
	for k in i1:
		if k not in i2: i2[k] = 0
	for k in i2:
		if k not in i1: i1[k] = 0

	# compare distances
	p1 = []
	p2 = []
	details = []
	for k in i1:
		p1.append(i1[k])
		p2.append(i2[k])
		details.append((k, i1[k], i2[k]))
	
	distance = manhattan(p1, p2)
	return distance, details



