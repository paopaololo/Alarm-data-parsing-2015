#!/usr/bin/python
import csv

def str2int(s, MeaninglessValue=0):
	# extract a meaningful integer from s (str). Returns the integer representing the first group of digits in the string
	# e.g. '   abc-147xyz23 ' returns -147
	# if no integer can be extracted, returns MeaninglessValue
	FirstDigitFound = False
	Sign = 1 # positive or negative indicator
	i = -1
	# find the first digit
	while (not FirstDigitFound) and (i < len(inps)-1):
		i += 1
		FirstDigitFound = inps[i].isdigit()
		# check for leading '-'
		if (inps[i] == '-'): Sign = -1
	if not FirstDigitFound: return MeaninglessValue # string contains no digits
	firstdigit = i # now we know the index of the first digit in the string
	NonDigitFound = False
	while (not NonDigitFound) and (i < len(inps)-1):
		i += 1
		NonDigitFound = not inps[i].isdigit()
	if NonDigitFound: lastdigit = i-1
	else: lastdigit = i # now we know the index of the last digit in this group
	return Sign * int(inps[firstdigit : lastdigit+1])


def StripHeaders(Data): # strip out page headers and footers from lines in Data. Return stripped data (list)

	def StripBlocks(Data, StartString, EndString): # strip blocks of lines starting with StartString and ending with EndString
		HeaderCount = 0
		LineNo = 0
		StrippedData = []
		InsideHeader = False
		EndStringFound = False
		while LineNo < len(Data):
			if Data[LineNo][:len(StartString)] == StartString:
				InsideHeader = True
				HeaderCount += 1
			elif Data[LineNo][:len(EndString)] == EndString:
				EndStringFound = True
			if not InsideHeader:
				StrippedData.append(Data[LineNo])
			if EndStringFound:
				EndStringFound = False
				InsideHeader = False
			LineNo += 1
		return (StrippedData, HeaderCount)

	def StripLines(Data, LineToStrip): # strip lines from data starting with LineToStrip
		LineNo = 0
		StrippedData = []
		while LineNo < len(Data):
			if Data[LineNo][:len(LineToStrip)] <> LineToStrip:
				StrippedData.append(Data[LineNo])
			LineNo += 1
		return StrippedData

	def StripLinesStartingWith(Data, SearchStr): # remove items from Data starting with SearchStr
		return [Str for Str in Data if not Str.startswith(SearchStr)]

	# strip headers
	(StrippedData, HeadersRemoved) = StripBlocks(Data, 'Control and Alarm Settings', 'System')
	# strip footers - consists only of line starting "Print Date:"
	StrippedData = StripLinesStartingWith(StrippedData, 'Print Date:')
	return (StrippedData, HeadersRemoved)

def SplitIntoTags(Data): # split Data into a list of separate lists, each for one tag
	# assumes a tag is a line starting with 612, and the preceding line (if any) is the 'Alarm Source'
	def NextLineWithTag(Data, StartLine): # return index of next item in Data after item StartLine that starts with '612', or -1 if none found
		Index = StartLine
		TagFound = False
		while (Index < len(Data)) and not TagFound:
			TagFound = Data[Index].strip().startswith('612')
			Index += 1
		if TagFound: return Index - 1 # dont understand
		else: return -1

	AlarmList = []
	TagLine = NextLineWithTag(Data, 0) # find first tag
	TagFound = (TagLine > -1)

	while TagFound:
		ThisAlarm = []
		if TagLine > 0: ThisAlarm.append(Data[TagLine-1]) # include 'Alarm Source'
		else: ThisAlarm.append('') # include empty 'Alarm Source' (for first alarm in the whole list)
		NextTagLine = NextLineWithTag(Data, TagLine + 1) # find next tag line
		if (NextTagLine == -1): # no next tag found
			TagFound = False
			NextTagLine = len(Data) # include all the data to the end of the list
		# include all lines from TagLine to NextTagLine (may include the 'Alarm Source' for the next alarm, if any; doesn't matter)
		ThisAlarm.extend(Data[TagLine : NextTagLine])
		TagLine = NextTagLine
		AlarmList.append(ThisAlarm)
	return AlarmList


def ParseAlarmsFromTag(TagData): # get alarms from tag data; return list of dictionaries per alarm in the tag

	def GetDataFromLine(Line): # return data from str provided
		DeleteFromEndOfLine = 'SEND OPERATOR TO VERIFY ROOT CAUSE FOR' # remove this text from the end of the line, if found
		Line = Line.strip() # get rid of leading and trailing spaces
		if Line == '---': return ''
		elif Line == 'ALARMS': return ''
		# elif Line == 'HOLD': return '00' # set all HOLD to 00, for the sake of importing
		elif Line[-len(DeleteFromEndOfLine):] == DeleteFromEndOfLine: return Line[:-len(DeleteFromEndOfLine)]
		else: return Line

	def GetNumberFromEndOfLine(Line): # return string from end of Line that contains only digits and - or .
		DigitFound = True
		Index = len(Line) - 1
		while DigitFound and Index > -1:
			DigitFound = (Line[Index] in '0123456789-.')
			Index -= 1
		return Line[Index+1:]
		
	# put several extra blank lines on the end of TagData to overcome parsing problems
	TagData.extend([''] * 20)

	ResultingAlarms = []
	CommonAlarmData = {}
	# copy the fixed fields into the output dictionary
	for (k, v) in FixedFields.iteritems():
		CommonAlarmData[k] = v
	# get common data for all alarms in the tag
	LineNo = 1
	ATagFound = False # check if the alarm is PA AA LA PDA TA FA
	ServiceLine = False # check if Service line is spanning across two lines.
	AllmissingbutEU = False
	AlarmTag = GetDataFromLine(TagData[LineNo])
	CommonAlarmData['Tag'] = AlarmTag
	ATagFound = AlarmTag.startswith('A' , 4) or AlarmTag.startswith('Y' , 4) or AlarmTag.startswith('A', 5) # checking if the data is '612XA or PDA or 612FY'
	LineNo += 1
	# next 3 lines will be either: Service + EU Low, EU High, EU or Service 1, Service 2, EU Low. Find out which one it is,
	# by checking the 3rd line - if digits, assume it's EU Low
	NextLine1 = GetDataFromLine(TagData[LineNo]).strip()
	NextLine2 = GetDataFromLine(TagData[LineNo + 1]).strip()
	NextLine3 = GetDataFromLine(TagData[LineNo + 2]).strip()
	NextLine4 = GetDataFromLine(TagData[LineNo + 3]).strip()
	NextLine5 = GetDataFromLine(TagData[LineNo + 4]).strip()
	if NextLine3 == '' and ATagFound:
		Service = NextLine1 + ' ' + NextLine2
		ServiceLine = True 
		EULow = '0'
		EUHigh = '0'
		EU = ''
		LineNo += 2	
	elif NextLine3.isdigit(): # it's the second pattern
		Service = NextLine1 + ' ' + NextLine2
		EULow = NextLine3
		EUHigh = GetDataFromLine(TagData[LineNo + 3])
		EU = GetDataFromLine(TagData[LineNo + 4])
		LineNo += 5
	# elif NextLine5 == '' and NextLine2 != '' and NextLine3 != '': # Service spanning across 2 lines with EU present but EUH and EUL missing
	#	Service = NextLine1 + ' ' + NextLine2
	#	EULow = '0'
	#	EUHigh = '0'
	#	EU = NextLine3
	#	LineNo += 3
	elif ATagFound: 
		Service = NextLine1.strip('-').strip()
		EULow = '0'
		EUHigh = '0'
		EU = ''
		LineNo += 1
	
	elif AlarmTag == '612FI -71014':
		Service = NextLine1.strip('-').strip()
		EULow = '0'
		EUHigh = '0'
		EU = ''
		LineNo += 1
		
	elif NextLine2 != '' and NextLine4 == '' and NextLine5 != '' : # EU present but EUH and EUL missing
		Service = NextLine1.strip('-').strip()
		EULow = '0'
		EUHigh = '0'
		EU = NextLine2
		AllmissingbutEU = True
		LineNo += 2
	else: # get EU Low from the end of Service, by chopping off digits and - signs
		Service = NextLine1
		EULow = GetNumberFromEndOfLine(Service)
		Service = Service[:-len(EULow)]
		EUHigh = NextLine2
		EU = NextLine3
		LineNo += 3
	print AlarmTag
	print Service
	CommonAlarmData['Description'] = Service  
	CommonAlarmData['EU Low'] = EULow
	CommonAlarmData['EU High'] = EUHigh
	CommonAlarmData['EU'] = EU
	# next line is LAHH setpoint if any
	HHSetpoint = GetDataFromLine(TagData[LineNo])
	# get data from following lines
	if ATagFound and not ServiceLine: 
		LineNo += 1 # For Alarms with tag A and Service not spanning across 2 lines, only skipping one line
	else: LineNo += 2
	NextLineC1 = GetDataFromLine(TagData[LineNo]).strip()
	NextLineC2 = GetDataFromLine(TagData[LineNo + 1]).strip()
	NextLineC3 = GetDataFromLine(TagData[LineNo + 2]).strip()
	NextLineC5 = GetDataFromLine(TagData[LineNo + 4]).strip()
	# print NextLineC2
	# print TagData
	
	if NextLineC5.startswith('LESS') or NextLineC5.startswith('TBD') or NextLineC5.startswith('NONE'): # when conseq spanning across two lines, the next line will be response
		Conseq = NextLineC1 + ' ' + NextLineC2
		Response = NextLineC5
		LineNo += 5
	elif NextLineC3.startswith('LESS') or NextLineC3.startswith('TBD') or NextLineC3.startswith('None'): # normal scenario  
		Conseq = NextLineC1
		Response = NextLineC3
		LineNo += 3
	elif NextLineC5.isdigit() or NextLineC5 == '': # when conseq spanning across two lines, and response missing
		Conseq = NextLineC1 + ' ' + NextLineC2
		Response = 'Missing in the input file provided by client.'
		LineNo += 4
	elif NextLineC3.isdigit() or NextLineC3 == '': # when only response missing
		Conseq = NextLineC1
		Response = 'Missing in the input file provided by client.'
		LineNo += 2
	elif AllmissingbutEU:
		Conseq = NextLineC1.strip('-').strip()
		Response = 'Missing in the input file provided by client.'
		LineNo += 1
	elif AlarmTag == '612FI -71014':
		Conseq = 'Missing in the input file provided by client.'
		Response = 'Missing in the input file provided by client.'
		
	CommonAlarmData['Conseq no action'] = Conseq.strip('-').strip()
	CommonAlarmData['User3'] = Response # time required for operator response
	
	if AllmissingbutEU: HSetpoint = ''
	else: HSetpoint = GetDataFromLine(TagData[LineNo])
	if AlarmTag == '612FI -71014': LineNo += 1
	else: LineNo += 2 # skip next line
	LSetpoint = GetDataFromLine(TagData[LineNo])
	LineNo += 2 # skip next line
	LLSetpoint = GetDataFromLine(TagData[LineNo]).split(' ', 1)[-1] # line is '--- ' followed by LL setpoint
	
	if HHSetpoint == HSetpoint == LSetpoint == LLSetpoint == '':
		if AlarmTag.startswith('612F'): LSetpoint = '0'
		if AlarmTag.startswith('612P'): HSetpoint = '0'
		if AlarmTag.startswith('612T'): HSetpoint = '0'
		if AlarmTag.startswith('612A'): HSetpoint = '0'
		if AlarmTag.startswith('612L'): HSetpoint = '0'
		if AlarmTag.startswith('612PD'): HSetpoint = '0'
	
	LineNo += 1
	# next line is: normal operating limit, control setpoint, process eng units
	NextLineChunks = GetDataFromLine(TagData[LineNo]).split(' ', 2) + ['', '', '']
	for (Index, Field) in enumerate(['Normal Op Limit', 'User2', 'User4']):
		CommonAlarmData[Field] = NextLineChunks[Index]
	LineNo += 1
	CommonAlarmData['Alarm Documentation'] = GetDataFromLine(TagData[LineNo])
	LineNo += 1
	CommonAlarmData['Alarm Source'] = GetDataFromLine(TagData[LineNo])
#	for (k, v) in CommonAlarmData.iteritems(): print k, ': ', v

	# generate alarm for each setpoint provided
	for (Sense, SetPoint) in [('HH', HHSetpoint), ('H', HSetpoint), ('L', LSetpoint), ('LL', LLSetpoint)]:
		if SetPoint.strip() <> '':
			ThisAlarm = dict(CommonAlarmData.iteritems()) # copy the dictionary of field values
			ThisAlarm['User Defined Setpoint'] = SetPoint
			ThisAlarm['Alarm Type'] = {'HH': 'High high', 'H': 'High', 'L': 'Low', 'LL': 'Low low'}[Sense]
			# make alarm name from tag by stripping spaces from tag, then replacing the character before the first - with AHH, AH, AL or ALL
			AlarmName = reduce(lambda a, b: a+b, [c for c in ThisAlarm['Tag'] if c <> ' '], '') # strip spaces
			HyphenIndex = AlarmName.find('-')
			if HyphenIndex > -1:
				AlarmName = AlarmName[:HyphenIndex-1] + 'A' + Sense + AlarmName[HyphenIndex:]
			ThisAlarm['Alarm Name'] = AlarmName
			ResultingAlarms.append(ThisAlarm)
	return ResultingAlarms


# main program
print "This is a script for building SK alarm database, by Peter Clarke, January 2015"
InputFileName = 'Alarm list raw 150128a.txt'
InputFile = open(InputFileName, 'r')

# read all the lines into a list
RawData = InputFile.readlines()
print "%d lines read from input file %s" % (len(RawData), InputFileName)

# strip out the page headers and footers
RawData, HeadersRemoved = StripHeaders(RawData)
print "%d headers and footers removed" % HeadersRemoved

# split the data into separate tags
RawTags = SplitIntoTags(RawData)
print "Data split into %d separate tags" % len(RawTags)

# make a CSV file for output
# allocation of user fields:
# User2 = control loop set point
# User3 = time required for operator response
# User4 = process engineering units
# OutFields shows all the fields to include in the output file
OutFields = ['Alarm Name', 'Tag', 'Description', 'Equipment', 'Alarm Documentation', 'Alarm Source', 'Normal Op Limit', 'User2', 'User3', 'User4', 'User Defined Setpoint', 'EU', 'EU Low', 'EU High', 'Conseq no action', 'Process Safe Time',  'Alarm Type', 'Is Analog', 'Time Index', 'Priority Is Overwritten', 'ImpactCat1', 'ImpactCat2', 'ImpactCat3', 'ImpactCat4', 'ImpactCat5', 'Include In Resp Report', 'Classif1', 'Classif2', 'Classif3', 'Classif4', 'Classif5', 'Classif6', 'Classif7', 'Classif8', 'Classif9', 'Classif10', 'Classif11', 'Classif12', 'Classif13', 'Classif14', 'Classif15', 'Classif16', 'Setpoint Selection', 'Shelving Days', 'Shelving Hours', 'Shelving Minutes', 'Enable Shelving', 'Current Status', 'Enabled']
# the following fields will have the same value for every alarm. NB Enabled is included here - is that right?
FixedFields = {'Time Index': '-1', 'Priority Is Overwritten': 'FALSE', 'ImpactCat1': '-1', 'ImpactCat2': '-1', 'ImpactCat3': '-1', 'ImpactCat4': '-1', 'ImpactCat5': '-1', 'Include In Resp Report': 'TRUE', 'Classif1': 'TRUE', 'Classif2': 'FALSE', 'Classif3': 'FALSE', 'Classif4': 'FALSE', 'Classif5': 'FALSE', 'Classif6': 'FALSE', 'Classif7': 'FALSE', 'Classif8': 'FALSE', 'Classif9': 'FALSE', 'Classif10': 'FALSE', 'Classif11': 'FALSE', 'Classif12': 'FALSE', 'Classif13': 'FALSE', 'Classif14': 'FALSE', 'Classif15': 'FALSE', 'Classif16': 'FALSE', 'Setpoint Selection': 'User Defined', 'Shelving Days': '0', 'Shelving Hours': '12', 'Shelving Minutes': '0', 'Enable Shelving': 'FALSE', 'Current Status': '0', 'Enabled': 'TRUE', 'Is Analog': 'TRUE'}
OutFile = open('Alarm list from Python script.csv', 'w')
Writer = csv.DictWriter(OutFile, OutFields, lineterminator='\r')

# write header row: field names
Writer.writerow(dict([(k, k) for k in OutFields]))

# temporary: discard all but the first tag
#RawTags = [RawTags[0]]

# parse each tag and write the corresponding alarm(s) to the file
TagCount = AlarmCount = 0
for Tag in RawTags:
	TagCount += 1
	Alarms = ParseAlarmsFromTag(Tag) # returns list of alarms, each one as a dictionary of fields and values
	for Alarm in Alarms:
		AlarmCount += 1
		Writer.writerow(Alarm)
print "Wrote %d alarms from %d tags" % (AlarmCount, TagCount)

OutFile.close()
