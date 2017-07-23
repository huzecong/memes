#!/usr/bin/env python
from __future__ import print_function

__author__ = 'huzecong'
__version__ = '0.1'


import argparse
import hashlib
import math
import os
import shutil
import subprocess
import sys
import tempfile


class Logging:
    @staticmethod
    def error(message):
        sys.stderr.write('Error: ' + message + '\n')
        raise
        sys.exit(1)

    @staticmethod
    def warning(message):
        sys.stderr.write('Warning: ' + message + '\n')

    @staticmethod
    def info(message):
        sys.stderr.write('Info: ' + message + '\n')


if __name__ != '__main__':
    Logging.error('This script should not be imported.')


parser = argparse.ArgumentParser(description='Find your memes when you want them.')
subparsers = parser.add_subparsers(metavar='command', dest='command', help='Valid commands are:')
parser.add_argument('-v', '--version', action='version', version='memes (version %s)' % __version__)

parser_add = subparsers.add_parser('add', help='Add meme (or folder of memes) to database',
                                   description='Add selected memes to database. Memes will be scanned for text using Tesseract OCR. You can also specify indexing keywords for single memes.')
parser_add.add_argument('-r', '--recursive', action='store_true',
                        help='Search recursively in folder for memes')
parser_add.add_argument('-v', '--verbose', action='store_true',
                        help='Print paths of all the added memes')
parser_add.add_argument('--keywords', metavar='"KEYWORDS"', default=None,
                        help='Specify keywords for single meme. When specifying multiple keywords, separate keywords using vertical bars (|). Be sure to wrap the keywords with quotation marks ("). This option has no effect when adding multiple memes (i.e. when the given path is a directory)')
parser_add.add_argument('--format', default="jpg,jpeg,png",
                        help='Filter acceptable file formats for memes. Specify formats using comma-separated (,) string of extensions. Note that the formats should be supported by the PIL library. This option has no effect when adding a single meme file')

parser_add.add_argument('path',
                        help='Path to meme file or folder containing memes')

parser_remove = subparsers.add_parser('remove', help='remove meme from database')

parser_list = subparsers.add_parser('list', help='list all memes in database')

parser_search = subparsers.add_parser('search', help='search for the meme you want',
                                      description='Search for the meme you want using keywords or phrases. Selected meme will be copied to your clipboard.')
parser_search.add_argument('-d', '--detail', action='store_true',
                           help='Display matching details (match score and matched phrases)')
parser_search.add_argument('-c', '--candidates', metavar='N', default=1,
                           help='Show the N most relevant matches. When N is greater than 1, and there are multiple matches, user will be prompted to choose from the top-ranked candidates')
parser_search.add_argument('--dry-run', action='store_true',
                           help='Do not copy selected meme to clipboard')
parser_search.add_argument('--hfs-paths', action='store_true',
                           help='Only output paths in HFS format, used in the meme macOS Service')
parser_search.add_argument('keywords', nargs='+',
                           help='Search keywords or phrases, multiple keywords are allowed')

args = parser.parse_args()

meme_path = os.path.expanduser('~/Library/Application Support/Memes')
database_path = os.path.join(meme_path, 'memes.db')


class Meme:
    def __init__(self, meme_id, meme_hash, filename, phrases):
        self.id = meme_id
        self.hash = meme_hash
        self.filename = filename
        self.phrases = phrases

    def _match_keyword(self, keyword):
        length = len(keyword)
        f = [0 for _ in range(length + 1)]
        for i in range(1, length + 1):
            f[i] = f[i - 1]
            for l in range(1, i + 1):
                chunk = keyword[(i - l):i]
                if chunk not in self.index[l]:
                    break
                f[i] = max(f[i], f[i - l] + l ** 2)
        return f[length]

    def match(self, keywords):
        if not hasattr(self, 'index'):
            max_length = max(len(phrase) for phrase in self.phrases)
            self.index = [set() for x in range(max_length + 1)]
            for phrase in self.phrases:
                length = len(phrase)
                for l in range(1, length):
                    for st in range(length - l):
                        self.index[l].add(phrase[st:(st + l)])
        
        max_score = sum(len(keyword) ** 2 for keyword in keywords)
        score = sum(self._match_keyword(keyword) for keyword in keywords)
        if score != 0: # normalize score
            score = 1.0 / (1 - math.log(float(score) / max_score))
        return score



def load_database(filename):
    '''
    File format:
    
    n_memes
    
    meme_id meme_hash meme_filename
    phrase phrase ...
    '''
    if not os.path.exists(filename):
        Logging.error('Failed to open database: file does not exist')
    try:
        f = open(filename, 'r')
        n_memes = int(f.next())
        memes = {}
        for i in range(n_memes):
            line = f.next()
            meme_id = int(line.split()[0])
            meme_hash = line.split()[1]
            meme_filename = ' '.join(line.split()[2:])
            if meme_filename == '':
                raise ValueError('File name is empty')
            meme_phrases = [phrase.decode('utf-8') for phrase in f.next().strip().split('|')]
            memes[meme_id] = Meme(meme_id, meme_hash, meme_filename, meme_phrases)
        return memes
    except:
        Logging.error('Failed to open database: database may be corrupt')


def save_database(filename, database):
    _, temp_path = tempfile.mkstemp()
    f = open(temp_path, 'w')
    temp = tempfile.NamedTemporaryFile()
    try:
        f.write(str(len(database)) + '\n')
        for meme in database.values():
            f.write(' '.join([str(meme.id), meme.hash, meme.filename]) + '\n')
            f.write(u'|'.join(meme.phrases).encode('utf-8') + '\n')
    except:
        Logging.error('Failed to save database: database may be corrupt')
    try:
        shutil.move(temp_path, filename)
    except:
        Logging.error('Failed to save database: cannot write to file')


if args.command == 'add':
    from PIL import Image
    import pytesseract

    try:
        args.format = ['.' + ext.lower() for ext in args.format.split(',')]
    except:
        Logging.error('Format specification is incorrect')
    if not os.path.exists(args.path):
        Logging.error("Path does not exist")

    if not os.path.exists(meme_path):
        os.makedirs(meme_path)
        # create emtpy database
        with open(database_path, 'w') as f:
            f.write('0\n')

    database = load_database(database_path)
    db_size = len(database)
    hashes = {meme.hash: meme.id for meme in database.values()}


    if os.path.isfile(args.path):
        files = [args.path]
    else:
        if args.keywords is not None:
            args.keywords = None
        if args.recursive:
            files = list(set(os.path.join(p, f) for p, _, fs in os.walk(args.path) for f in fs))
        else:
            files = os.listdir(args.path)
    files = [f for f in files if os.path.splitext(f)[-1].lower() in args.format]
    Logging.info('%d file%s found. Scanning...' % (len(files), 's' if len(files) != 1 else ''))


    def filter_phrase(phrase):
        is_chinese = lambda c: u'\u4e00' <= c <= u'\u9fff'
        is_alpha = lambda c: 'a' <= c <= 'z' or 'A' <= c <= 'Z'
        is_num = lambda c: '0' <= c <= '9'
        is_punct = lambda c: c in ',.?!:-&'
        is_valid = lambda c: is_chinese(c) or is_alpha(c) or is_num(c) or is_punct(c) or c == ' '
        raw_phrase = ' '.join(unicode(filter(is_valid, phrase)).split())
        length = len(raw_phrase)
        phrase = ''
        for i in range(length):
            if raw_phrase[i] == ' ':
                if i == length - 1 or i == 0: continue
                lc, rc = raw_phrase[i - 1], raw_phrase[i + 1]
                if is_chinese(lc) and is_chinese(rc): continue
                if is_punct(lc) and is_punct(rc): continue
            phrase += raw_phrase[i]
        return phrase

    meme_count = 0
    for file_path in sorted(files):
        cur_id = db_size + meme_count
        new_filename = str(cur_id) + os.path.splitext(file_path)[-1]
        new_path = os.path.join(meme_path, new_filename)
        shutil.copy(file_path, new_path)
        try:
            image = Image.open(new_path)
        except:
            Logging.warning("File '%s' is not a supported image file, skipping" % file_path)
            continue

        meme_hash = hashlib.md5(open(new_path).read()).hexdigest()
        if meme_hash in hashes:
            Logging.warning("File '%s' is already stored in database as id %d" % (file_path, hashes[meme_hash]))
            continue

        if args.keywords is None:
            # PSM 6: Assume a single uniform block of text
            phrases1 = pytesseract.image_to_string(image, lang='chi_sim', config='--psm 6')
            # PSM 12: Sparse text with OSD
            phrases2 = pytesseract.image_to_string(image, lang='chi_sim', config='--psm 12')
            phrases = [phrases1, phrases2]
        else:
            phrases = args.keywords.split('|')
        phrases = map(filter_phrase, [phrases1, phrases2])
        phrases = filter(lambda p: len(p) > 0, phrases)
        if len(phrases) == 0:
            Logging.warning("Meme from file '%s' does not contain recognizable text, skipping" % file_path)
            continue

        database[cur_id] = Meme(cur_id, meme_hash, new_filename, phrases)
        hashes[meme_hash] = cur_id
        meme_count += 1
        if args.verbose:
            Logging.info(u"Meme from file '%s' scanned, keywords: %s" % (file_path, ' | '.join(phrases)))

    if meme_count > 0:
        save_database(database_path, database)
    Logging.info("%d new meme%s added to database" % (meme_count, 's' if meme_count != 1 else ''))


elif args.command == 'search':
    if not os.path.exists(meme_path):
        Logging.error("There are no memes in the databse yet.")

    Logging.info("Search keywords: " + ' | '.join(args.keywords))
    keywords = [keyword.decode('utf-8').strip() for keyword in args.keywords]

    database = load_database(database_path)
    n_cand = int(args.candidates)
    scores = [(meme.match(keywords), meme.id) for meme in database.values()]
    scores = filter(lambda (s, _): s > 0, sorted(scores, key=lambda (s, _): s, reverse=True)[:n_cand])

    if len(scores) == 0:
        Logging.info("No matching memes found")
        sys.exit(0)
    
    file_paths = [os.path.join(meme_path, database[meme_id].filename) for _, meme_id in scores]
    if args.dry_run:
        if args.hfs_paths:
            file_paths = ['Macintosh HD' + path.replace('/', ':') for path in file_paths]
        print('\n'.join(file_paths))
        sys.exit(0)
    else:
        subprocess.call(['qlmanage', '-p'] + file_paths)

else:
    "Command '%s' is not supported yet." % args.command

