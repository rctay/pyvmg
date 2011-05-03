import re
import csv
import datetime

def escapexml(xmldata):
    xmldata = xmldata.replace('&', '&amp;')
    xmldata = xmldata.replace('<', '&lt;')
    xmldata = xmldata.replace('>', '&gt;')
    xmldata = xmldata.replace('"', '&quot;')
    return xmldata

def datecmp(x,y):
    if x['date'] < y['date']:
        return -1
    elif x['date'] == y['date']:
        return 0
    else:
        return 1

class VMGReader(object):
    """Reader for a .vmg file to get back the telephone number, date, body
    """
    def __init__(self):
        """Initialize with the required regexes
        """
        self.telre = re.compile(r'TEL:(\+?\d+)')
        self.datere = re.compile(r'X-NOK-DT:([\dTZ]+)')
        self.bodyre = re.compile(r'Date:[\d.: ]+\n(.*)END:VBODY',re.DOTALL)

    def read(self, filename):
        """Open a .vmg file and remove the NULL characters and store the text message
        """
        self.filename = filename
        self.message = open(filename, 'r').read()
        self.message = self.message.replace('\0', '')

    def process(self):
        """Parse the message and return back a dictionary with
        telephone number, date and body of message
        """
        data = {}
        telmatch = self.telre.search(self.message)
        if telmatch:
            data['telno'] = telmatch.group(1)
        else:
            data['telno'] = ''
        datematch = self.datere.search(self.message)
        if datematch:
            data['date'] = datematch.group(1)
            try:
                data['date']  = datetime.datetime.strptime(data['date'], '%Y%m%dT%H%M%SZ')
            except ValueError:
                # Use Epoch as date if no date was available
                data['date'] = datetime.datetime(1970, 1, 1, 0, 0)
        bodymatch = self.bodyre.search(self.message)
        if bodymatch:
            data['body'] = escapexml(bodymatch.group(1))[:-1]
        else:
            data['body'] = ''
        return data

class Writer(object):
    """Base class for a writer object to convert all VMG files to a single file
    """

    DATETIME_FORMAT = '%Y-%m-%d %H:%M:%S'

    def __init__(self, file):
        """Create a file writer object with the filename specified
        """
        self.file = file

    def process(self, filenames):
        """Given a list .vmg filenames, process them and store as a list
        """
        reader = VMGReader()
        self.messages = []
        for f in filenames:
            reader.read(f)
            self.messages.append(reader.process())
        self.messages.sort(datecmp)     # Sort the messages according to date

class XMLWriter(Writer):
    """Writer object for XML file as output
    """
    def write(self):
        """Read every message in the list and write to a XML file
        """
        self.file.write('<messages>')
        tmpl = "<message><tel>%s</tel><date>%s</date><body>%s</body></message>"
        for msg in self.messages:
            xmlstr = tmpl %(msg['telno'], msg['date'].strftime(self.DATETIME_FORMAT), msg['body'])
            self.file.write(xmlstr)
        self.file.write('</messages>')

class CSVWriter(Writer):
    """Writer object for CSV file as output
    """
    def write(self):
        """Read every message in the list and write to a CSV file
        """
        fn = csv.writer(self.file).writerow
        fn(('telno', 'date', 'body'))
        for msg in self.messages:
            fn((msg['telno'], msg['date'].strftime(self.DATETIME_FORMAT), msg['body']))

class TextWriter(Writer):
    """Writer object for text file as output

    Format is
    +919900123456 - 2008-05-26 12:42:32
    Message contents goes here

    +919900123456 - 2008-05-26 12:50:32
    Second message contents goes here

    Ignores empty messages
    """
    def write(self):
        """Read every message in the list and write to a CSV file
        """
        tmpl = "%s - %s\n%s\n\n"
        for msg in self.messages:
            if msg['telno'] == '':
                continue
            txtstr = tmpl %(msg['telno'], msg['date'].strftime(self.DATETIME_FORMAT), msg['body'])
            self.file.write(txtstr)


def main():
    import glob
    from optparse import OptionGroup, OptionParser
    import os
    import stat
    import sys

    parser = OptionParser(usage="Usage: $prog[ options] file/dir...")

    formats = {
        'xml': XMLWriter,
        'csv': CSVWriter,
        'txt': TextWriter,
    }
    parser.add_option('-f', '--format', dest="format",
        choices=formats.keys(),
        help="one of: %s" % ", ".join(formats.keys()))

    parser.add_option('-o', '--output', dest="filename", default=None,
        help="file to write to; if not specified, writes to stdout")

    (options, args) = parser.parse_args()
    if not len(args) or not options.format:
        parser.print_help()
        return

    if options.filename:
        outfile = open(options.filename, 'w')
    else:
        outfile = sys.stdout

    cls = formats[options.format]
    writer = cls(outfile)

    try:
        filenames = []
        for spec in args:
            st = os.stat(spec)
            if stat.S_ISDIR(st.st_mode):
                filenames.extend(glob.glob(spec + '/*.vmg'))
            elif stat.S_ISREG(st.st_mode):
                filenames.append(spec)
            else:
                raise os.error
        writer.process(filenames)
    except os.error as e:
        sys.stderr.write("%s\n" % str(e))
        return

    writer.write()

    if options.filename:
        outfile.close()


if __name__ == '__main__':
    main()
