import discord
import os
from server import ping
import re
import datetime
#import PIL
#import pytesseract

client = discord.Client()
#pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

#on_message function is starting point for all searching
#Generally function order is on_message() -> search() -> messageParser() -> parsedisvalid() -> messageisvalid() -> display()
@client.event
async def on_message(message):
  if message.author == client.user:
    return
  
  if message.content.startswith("s!help"):
    helpmsg = """Discord bot implementing a better way to search.
  
Commands list:
`!help`: Shows list of commands and operators.
`s!search`: Results contain search message within contents, sorted from newest to oldest.
`s!showall`: Same results as `s!search` but displays every message found. Not recommended for broad searches in servers with high message counts.
`s!oldest`: Same results as `s!search` but in reverse order, displayed from oldest to most recent.
`s!relevent`: Sorts results by frequency of search term appearances within the contents of the results.
`s!exact`: Shows messages where the entire content of the message is exactly the message being searched, results are case sensitive. Search operators cannot be used with `s!exact`.
`s!regex`: Assumes search to be using regular expressions as search operators. Other search operators cannot be used with `s!regex`.
    
All commands with exception to `s!oldest` and `s!relevent` sort results from most recent to oldest. All commands with exception to `s!showall` display only the first 10,000 characters of results as to not flood the channel with messages. Searching works by checking whether every message contains each word being searched within its contents, not necessarily in order and not necessarily case sensitive, with exception to `s!exact` and `s!regex`. Discord's integrated search functions are usable, as well as more advanced search operators used in other search engines.""" #\n`s!image`: Results contain search message within any attached image, using artificial intelligence to read any text within the image. This uses an implementation of Google's Tesseract OCR, and results may not be entirely accurate.
    helpmsg2 = """
A list of search operators and what they do below:
`from:`user: Results only include messages sent by the specified user. Discord tag or User ID required.
`mentions:`user: Results only include messages that tag the specified user. Discord tag or User ID required.
`has:`link OR embed OR file: Results only include messages that contain a link, an embed, or a file attached.
`before:`date: Results only include messages sent before specified date, in `YYYY-MM-DD` format.
`during:`date: Results only include messages sent during specified date, in `YYYY-MM-DD` format.
`after:`date: Results only include messages sent after specified date, in `YYYY-MM-DD` format.
`in:`channel: Results only include messages sent in specified channel.
`pinned:`True OR False: Results only include messages that are / aren't pinned.
`filetype:`file extension: Results only include messages with attatchment of specified file extension.
`daterange:`date..date: Results only include messages sent between the two dates specified, in `YYYY-MM-DD..YYYY-MM-DD` format.
`limit:n`: Speeds up search by limiting the number of messages searched to `n` newest messages. If using `s!oldest` with `limit:`, results will show the oldest messages within the most recent `n` messages, not the `n` oldest messages. Using `limit:` is highly recommended for servers with high message counts."""
    helpmsg3 = """
`\" \"` / `+`: Everything within quotation marks or after a plus sign will be taken as exact, results are case sensitive.
`OR` / `|`: Shows results which match with either the word directly before or after the operator (note: due to implementation, `OR` operator will not work with Discord operators or `AROUND(n)` / `near(n)` operator).
`AROUND(n)` / `near(n)`: Results only include messages where the words directly before and after the operator are no more than `n` words apart.
`..`: If used between two different numbers, results will include any number within the range of the two numbers, inclusive.
`-`: Removes results containing everything after the hypen."""
    
    await message.channel.send(helpmsg)
    await message.channel.send(helpmsg2)
    await message.channel.send(helpmsg3)
  
  if message.content.startswith("s!search "):
    result = await search(message.content[9:], message)
    await display(result, message.channel)
  
  if message.content.startswith("s!showall "):
    result = await search(message.content[10:], message)
    #display() called with showall parameter True
    await display(result, message.channel, True)
  
  if message.content.startswith("s!oldest "):
    toReverse = await search(message.content[9:], message)
    result = tuple(reversed(toReverse))
    await display(result, message.channel)
  
  if message.content.startswith("s!relevent "):
    searchTerms = message.content[11:].split()
    unsorted = await search(message.content[11:], message)
    #Create dict pairing result messages with frequency of search terms within content 
    csorted = ()
    freq = {}
    for i in unsorted:
      fcount = 0
      for w in searchTerms:
        fcount = fcount + i.content.count(w)
      freq[i] = fcount
    
    #Sort results by frequency
    for j in sorted(freq.items(), key = lambda i: i[1], reverse = True):
      csorted = csorted + (j[0],)
    result = csorted
    await display(result, message.channel)
  
  if message.content.startswith("s!exact "):
    result = await search(message.content, message)
    await display(result, message.channel)
  
  if message.content.startswith("s!regex "):
    result = ()
    #Takes search content as regex pattern
    pattern = message.content[8:]
    await message.channel.send("Searching in progress...")
    for ch in message.guild.text_channels:
      if ch.permissions_for(message.author).read_message_history:
        try:
          async for msg in ch.history(limit = None):
            match = re.search(pattern, msg.content)
            if match != None and msg.author != client.user:
              result = result + (msg,)
        except Exception as e:
          print(e)
          print("Exception in " + ch.name)
    #Sort results by created_at since it gets messages from all channels
    result = tuple(sorted(result, key = lambda i: i.created_at, reverse = True))
    await display(result, message.channel)
  
  #if message.content.startswith("s!image "):
  #  result = await search(message.content, message, True)
  #  await display(result, message.channel)

def messageParser(content):
  opers = ["from:", "mentions:", "has:", "before:", "during:", "after:", "in:", "pinned:", "filetype:", "daterange:", "limit:", "+", "\"", "OR", "|", "AROUND(", "near(", "..", "-"]
  if all(oper not in content for oper in opers):
    return False
  
  parsedvars = {} #Main dict to be returned, other lists will be added within it if applicable
  exactlist = []
  anylist = []
  proxlist = []
  #Fixedstring to remove all operators from content for returning
  fixedstring = content
  
  #Check for value of integrated Discord operators as well as daterange: and limit:
  for o in opers[:11]:
    if fixedstring.find(o) != -1:
      #Get index of value immediately following operator
      sIndex = fixedstring.find(o) + len(o)
      if fixedstring[sIndex:].find(" ") != -1:
        eIndex = sIndex + fixedstring[sIndex:].find(" ")
        parsedvars[o] = fixedstring[sIndex:eIndex]
        fixedstring = fixedstring[:fixedstring.find(o)] + fixedstring[eIndex:]
      else:
        parsedvars[o] = fixedstring[sIndex:]
        fixedstring = fixedstring[:fixedstring.find(o)]
  
  #Check for OR or | within content, parse words or phrases around the operator
  if fixedstring.find("OR") != -1 or fixedstring.find("|") != -1:
    iterstring = fixedstring
    #Iterate over each match
    for i in re.finditer(r"(OR)|(\|)", iterstring):
      #If match isnt within bounds of exact operators "" or +
      if (fixedstring.find("+") == -1 or fixedstring.find("+") > i.start()) and (fixedstring[:i.start()].count("\"") % 2 == 0 or fixedstring[i.end():].count("\"") % 2 == 0):
        w1eIndex = i.start()
        flag = True
        special = []
        snum = 0
        
        #Check if whitespace before start of match exists
        j = iterstring[:i.start() - 1].rfind(" ")
        if j != -1:
          flag = False
          w1sIndex = j + 1
        
        #Check if word1 should be group of words taken as exact with ""
        j = iterstring[:i.start()].rfind("\"")
        #If " exists and another " exists before it and that "" is closer than the closest whitespace
        if j != -1 and iterstring[:j].rfind("\"") != -1 and j > iterstring[:i.start() - 1].rfind(" "):
          flag = False
          w1sIndex = iterstring[:j].rfind("\"") + 1
          w1eIndex = j
        
        #Check if word1 is n..n operator
        j = re.findall(r"\d+\.\.\d+", iterstring[:i.start()])
        if len(j) > 0:
          #Get closest n..n before OR oper if multiple exist
          j = j[-1]
        #Check if match exists and that match is closer than the closest whitespace
        if j != [] and iterstring[:i.start()].rfind(j) > iterstring[:i.start() - 1].rfind(" "):
          flag = False
          nums = j.split("..")
          try:
            num1 = int(nums[0])
            num2 = int(nums[1])
            if num1 < num2:
              special.append(list(range(num1, num2 + 1)))
            else:
              special.append(list(range(num1, num2 + 1, -1)))
          except:
            print("num1 or num2 not converted to int")
          w1sIndex = iterstring[:i.start()].rfind(j)
          w1eIndex = iterstring[:i.start()].rfind(j) + len(j)
          snum = snum + 1
        
        if flag:
          w1sIndex = 0
        w2sIndex = i.end()
        flag = True
        
        #Check if whitespace exists after word2
        j = iterstring[i.end() + 1:].find(" ") + i.end() + 1
        if j != (-1 + i.end() + 1):
          flag = False
          w2eIndex = w2sIndex + j
        
        #Check if word2 should be group of exact words with "" or + operators
        j = iterstring[i.end():].find("\"") + i.end()
        if j != (-1 + i.end()) and iterstring[j + 1:].find("\"") != -1 and (j < iterstring[i.end() + 1:].find(" ") + i.end() + 1 or iterstring[i.end() + 1:].find(" ") == -1):
          flag = False
          w2eIndex = iterstring[j + 1:].find("\"") + j + 1
          w2sIndex = j + 1
        
        j = iterstring[i.end():].find("+") + i.end()
        if j != (-1 + i.end()) and iterstring[i.end():j].strip() == "":
          flag = False
          w2eIndex = len(iterstring)
          w2sIndex = j + 1
        
        #Check if word2 is n..n with first match after OR oper
        j = re.search(r"\d+\.\.\d+", iterstring[i.end():])
        if j != None and ((j.span()[0] + i.end()) < (iterstring[i.end() + 1:].find(" ") + i.end() + 1) or iterstring[i.end() + 1:].find(" ") == -1):
          flag = False
          nums = j.group().split("..")
          try:
            num1 = int(nums[0])
            num2 = int(nums[1])
            if num1 < num2:
              special.append(list(range(num1, num2 + 1)))
            else:
              special.append(list(range(num1, num2 + 1, -1)))
          except:
            print("num1 or num2 not converted to int")
          w2sIndex = j.span()[0] + i.end()
          w2eIndex = j.span()[1] + i.end()
          snum = snum + 2
        
        if flag:
          w2eIndex = len(iterstring)
        word1 = iterstring[w1sIndex:w1eIndex]
        word2 = iterstring[w2sIndex:w2eIndex]
        #Check for group of OR opers to extend previous anylist (word1 OR word2 OR word3 etc)
        if len(word1.strip()) == 0 and len(anylist) > 0:
          if len(special) != 0:
            anylist[-1].extend(special[0])
          else:
            anylist[-1].extend([word2.strip()])
        else:
          #Check if word1 or word2 were n..n to correctly append their ranges to anylist
          if len(special) != 0:
            if snum == 1:
              special[0].append(word2.strip())
              anylist.append(special[0])
            elif snum == 2:
              special[0].append(word1.strip())
              anylist.append(special[0])
            elif snum == 3:
              special[0].extend(special[1])
              anylist.append(special[0])
          else:
            anylist.append([word1.strip(), word2.strip()])

        #Remove word1 operator and word2 by replacing them with whitespace to keep indexes the same between iteration
        temp = ""
        for i in range(len(iterstring[w1sIndex:w2eIndex])):
          temp = temp + " "
        iterstring = iterstring[:w1sIndex] + temp + iterstring[w2eIndex:]
        fixedstring = iterstring
  
  #Check for AROUND(n) or near(n) within content, parse proximity and words or phrases around the operator
  #Very similar parsing to OR / | operators
  if (fixedstring.find("AROUND(") != -1 and fixedstring[fixedstring.find("AROUND("):].find(")") != -1) or (fixedstring.find("near(") != -1 and fixedstring[fixedstring.find("near("):].find(")") != -1):
    iterstring = fixedstring
    toremove = []
    for i in re.finditer(r"(AROUND\(\d+\))|(near\(\d+\))", iterstring):
      if (fixedstring.find("+") == -1 or fixedstring.find("+") > i.start()) and (fixedstring[:i.start()].count("\"") % 2 == 0 and fixedstring[i.end():].count("\"") % 2 == 0):
        flag = True
        special = []
        snum = 0
        if re.search(r"match=\'AROUND\(", str(i)) != None:
          nsIndex = i.start() + 7
        else:
          nsIndex = i.start() + 5
        neIndex = i.end() - 1
        proximity = iterstring[nsIndex:neIndex]
        
        j = iterstring[:i.start() - 1].rfind(" ")
        if j != -1:
          flag = False
          word1 = iterstring[j:i.start()]
        
        j = iterstring[:i.start()].rfind("\"")
        if j != -1 and iterstring[:j].rfind("\"") != -1 and j > iterstring[:i.start() - 1].rfind(" "):
          flag = False
          word1 = iterstring[iterstring[:j].rfind("\"") + 1:j]
        
        j = re.findall(r"\d+\.\.\d+", iterstring[:i.start()])
        if len(j) > 0:
          j = j[-1]
        if j != [] and iterstring[:i.start()].rfind(j) > iterstring[:i.start() - 1].rfind(" "):
          flag = False
          nums = j.split("..")
          try:
            num1 = int(nums[0])
            num2 = int(nums[1])
            if num1 < num2:
              special.append(list(range(num1, num2 + 1)))
            else:
              special.append(list(range(num1, num2 + 1, -1)))
          except:
            print("num1 or num2 not converted to int")
          word1 = iterstring[iterstring[:i.start()].rfind(j):iterstring[:i.start()].rfind(j) + len(j)]
          snum = snum + 1
        
        if flag:
          word1 = iterstring[:i.start()]
        flag = True
        
        if iterstring[i.end() + 1:].find(" ") != -1:
          flag = False
          word2 = iterstring[i.end():(i.end() + 1 + iterstring[i.end() + 1:].find(" "))]
        
        j = iterstring[i.end():].find("\"") + i.end()
        if j != (-1 + i.end()) and iterstring[j + 1:].find("\"") != -1 and (j < iterstring[i.end():].find(" ") + i.end() or iterstring[i.end():].find(" ") == -1):
          flag = False
          word2 = iterstring[j + 1:iterstring[j + 1:].find("\"") + j + 1]
        
        j = iterstring[i.end():].find("+") + i.end()
        if j != (-1 + i.end()) and iterstring[i.end():j].strip() == "":
          flag = False
          word2 = iterstring[j + 1:]
        
        j = re.search(r"\d+\.\.\d+", iterstring[i.end():])
        if j != None:
          if ((j.span()[0] + i.end()) < (iterstring[i.end() + 1:].find(" ") + i.end() + 1) or iterstring[i.end() + 1:].find(" ") == -1):
            flag = False
            nums = j.group().split("..")
            try:
              num1 = int(nums[0])
              num2 = int(nums[1])
              if num1 < num2:
                special.append(list(range(num1, num2 + 1)))
              else:
                special.append(list(range(num1, num2 + 1, -1)))
            except:
              print("num1 or num2 not converted to int")
            word2 = iterstring[j.span()[0] + i.end():j.span()[1] + i.end()]
            snum = snum + 2
        
        if flag:
          word2 = iterstring[i.end():]
        if len(special) != 0:
          if snum == 1:
            proxlist.append([proximity, special[0], word2.strip()])
          elif snum == 2:
            proxlist.append([proximity, word1.strip(), special[0]])
          elif snum == 3:
            proxlist.append([proximity, special[0], special[1]])
        else:
          proxlist.append([proximity, word1.strip(), word2.strip()])
        
        word1 = word1.strip()
        #r[0] = start of word1
        #r[1] = len from start of word1 to end of word2
        if (i.start() - len(word1) - 1) == -1 or iterstring[i.start() - 1] != " ":
          toremove.append([i.start() - len(word1), len(iterstring[i.start() - len(word1):i.end() + len(word2) + 1])])
        else:
          toremove.append([i.start() - len(word1) - 1, len(iterstring[i.start() - len(word1) - 1:i.end() + len(word2) + 1])])
    for r in toremove:
      temp = ""
      for i in range(r[1]):
        temp = temp + " "
      fixedstring = fixedstring[:r[0]] + temp + fixedstring[r[0] + r[1]:]

  #Check if + operator is used for exact results within content
  if fixedstring.find("+") != -1:
    index = fixedstring.find("+")
    exactlist.append(fixedstring[index + 1:])
    fixedstring = fixedstring[:index]

  #Check if " " operator is used for exact results within content
  if fixedstring.count("\"") > 1:
    toremove = []
    #Pattern = any amount of characters between ""
    for i in re.finditer(r"\"(.*?)\"", fixedstring):
      exactlist.append(i.group().strip("\""))
      toremove.append(i.group())
    for r in toremove:
      fixedstring = fixedstring.replace(r, "")

  #Check for n..n operator within content, parse numbers around it to get list of nums
  if fixedstring.find("..") != -1:
    iterstring = fixedstring
    toremove = []
    for i in re.finditer(r"\.\.", iterstring):
      #Get indexes of numbers separated by each ..
      n1eIndex = i.start()
      if iterstring[:n1eIndex].rfind(" ") != -1:
        n1sIndex = iterstring[:n1eIndex].rfind(" ")
      else:
        n1sIndex = 0
      n2sIndex = i.start() + 2
      if iterstring[n2sIndex:].find(" ") != -1:
        n2eIndex = n2sIndex + iterstring[n2sIndex:].find(" ")
      else:
        n2eIndex = len(iterstring)
      num1 = iterstring[n1sIndex:n1eIndex]
      num2 = iterstring[n2sIndex:n2eIndex]
      try:
        #Validate num1 and num2 can be converted to int
        num1 = int(num1)
        num2 = int(num2)
        #Get range of numbers if valid
        if num1 < num2:
          anylist.append(list(range(num1, num2 + 1)))
        else:
          anylist.append(list(range(num1, num2 + 1, -1)))
        toremove.append(iterstring[n1sIndex:n2eIndex])
      except:
        print("num1 or num2 not converted to int")
    for r in toremove:
      fixedstring = fixedstring.replace(r, "")

  #Check if - operator is used within content for removing words or phrases
  if fixedstring.find("-") != -1:
    index = fixedstring.find("-")
    parsedvars["without"] = fixedstring[index + 1:]
    fixedstring = fixedstring[:index]
  
  parsedvars["around"] = proxlist
  parsedvars["any"] = anylist
  parsedvars["exact"] = exactlist
  parsedvars["content"] = fixedstring
  return parsedvars

async def search(content, message):#, simage = False):
  channels = message.guild.text_channels
  #searchlist = [] #List to be returned after validation and sorting
  searchtup = () #Tuple to be returned after validation and sorting
  await message.channel.send("Searching in progress...")
  
  #s!exact command sends full content to search() so that it doesn't go through messageParser()
  if content.startswith("s!exact "):
    for ch in channels:
      if ch.permissions_for(message.author).read_message_history:
        try:
          #No need to get limit since message is being taken as exact and limit: operator can't be used
          async for msg in ch.history(limit = None):
            #No need to go through parsedisvalid or messageisvalid since nothing is parsed from content
            if msg.content == content[8:] and msg.author != client.user:
              #searchlist.append(msg)
              searchtup = searchtup + (msg,)
        except Exception as e:
          print(e)
          print("Exception in " + ch.name)
    #searchlist = sorted(searchlist, key = lambda i: i.created_at, reverse = True)
    searchtup = tuple(sorted(searchtup, key = lambda i: i.created_at, reverse = True))
    #return searchlist
    return searchtup
  
  parsed = messageParser(content)
  #messageParser will return False if no operators within content
  if (parsed == False):
    #List of commands to ignore if msg contains
    cmd = ["s!help", "s!search ", "s!showall ", "s!oldest ", "s!relevent ", "s!exact ", "s!regex ", "s!image "]
    #if simage:
    #  for ch in channels:
    #    if ch.permissions_for(message.author).read_message_history:
    #      try:
    #        async for msg in ch.history(limit = None):
    #          for a in msg.attachments:
    #            #Get fp object from file attachment so Pillow can open it
    #            f = await a.to_file()
    #            f = f.fp
    #            #Each word in content shows up at least once in return string of image_to_string, case insensitive
    #            if all(words in pytesseract.image_to_string(PIL.Image.open(f)).lower() for words in content.lower().split()) and msg.author != client.user and all(c not in msg.content for c in cmd):
    #              #searchlist.append(msg)
    #              searchtup = searchtup + (msg,)
    #      except Exception as e:
    #        print(e)
    #        print("Exception in " + ch.name)
    #else: #Remember to indent next lines if uncommented
    for ch in channels:
        if ch.permissions_for(message.author).read_message_history:
          try:
            async for msg in ch.history(limit = None):
              #Each word in content shows up at least once in msg, case insensitive
              if all(words in msg.content.lower() for words in content.lower().split()) and msg.author != client.user and all(c not in msg.content for c in cmd):
                #searchlist.append(msg)
                searchtup = searchtup + (msg,)
          except Exception as e:
            print(e)
            print("Exception in " + ch.name)
    #searchlist = sorted(searchlist, key = lambda i: i.created_at, reverse = True)
    searchtup = tuple(sorted(searchtup, key = lambda i: i.created_at, reverse = True))
    #return searchlist
    return searchtup
  
  validate = parsedisvalid(parsed) #parsedisvalid returns error string or "" if everything is valid
  if validate != "":
    await message.channel.send(validate)
    return []
  
  if "limit:" in parsed:
    #Limit 2 higher to ignore initial search command and "Searching in progress..." messages
    lim = int(parsed["limit:"]) + 2
  else:
    lim = None
  if "in:" in parsed:
    #Check if in: command is valid channel
    if parsed["in:"] in "".join(str(channels)):
      ch = discord.utils.get(channels, name = parsed["in:"])
      #Only check specified channel instead of all channels if valid, massive time save even though code gets repeated
      if ch.permissions_for(message.author).read_message_history:
        try:
          #if simage:
          #  async for msg in ch.history(limit = lim):
          #    #messageisvalid img parameter passed as True
          #    if await messageisvalid(msg, parsed, True):
          #      #searchlist.append(msg)
          #      searchtup = searchtup + (msg,)
          #else:
            async for msg in ch.history(limit = lim):
              if await messageisvalid(msg, parsed):
                #searchlist.append(msg)
                searchtup = searchtup + (msg,)
        except Exception as e:
          print(e)
          print("Exception in " + ch.name)
      #No need to sort since only 1 channel searched
      #return searchlist
      return searchtup
    else:
      await message.channel.send("Invalid search operator. Value of `in:` must be valid channel name that you have message history permissions for.")
      return []
  
  #if simage:
  #  for ch in channels:
  #    if ch.permissions_for(message.author).read_message_history:
  #      try:
  #        async for msg in ch.history(limit = lim):
  #          #messageisvalid img parameter passed as True
  #          if await messageisvalid(msg, parsed, True):
  #            #searchlist.append(msg)
  #            searchtup = searchtup + (msg,)
  #      except Exception as e:
  #        print(e)
  #        print("Exception in " + ch.name)
  #else:
  for ch in channels:
      if ch.permissions_for(message.author).read_message_history:
        try:
          async for msg in ch.history(limit = lim):
            if await messageisvalid(msg, parsed):
              #searchlist.append(msg)
              searchtup = searchtup + (msg,)
        except Exception as e:
          print(e)
          print("Exception in " + ch.name)
  
  #searchlist = sorted(searchlist, key = lambda i: i.created_at, reverse = True)
  searchtup = tuple(sorted(searchtup, key = lambda i: i.created_at, reverse = True))
  #Searchtup filled with at most lim messages from each channel, trim to lim - 2 messages total
  #if lim != None and len(searchlist) > lim - 2:
    #searchlist = searchlist[:lim - 2]
  if lim != None and len(searchtup) > lim - 2:
    searchtup = searchtup[:lim - 2]
  #return searchlist
  return searchtup

def parsedisvalid(parsed):
  if "limit:" in parsed and parsed["limit:"].isnumeric() == False:
    return "Invalid search operator. Value of `limit:` must be positive integer number."
  
  if "around:" in parsed and parsed["around"][0].isnumeric() == False:
    return "Invalid search operator. Value of `AROUND()` or `near()` must be positive integer number."
  
  #Regex pattern for from: = any amount of numbers OR any characters followed by # and 4 digit number
  if "from:" in parsed and re.match("(\d+)|(.+#\d{4})", parsed["from:"]) == None:
    return "Invalid search operator. Value of `from:` must be Discord account name including discriminator or Discord account ID."
  
  #Regex pattern for mentions: is same as from: pattern
  if "mentions:" in parsed and re.match("(\d+)|(.+#\d{4})", parsed["mentions:"]) == None:
    return "Invalid search operator. Value of `mentions:` must be Discord account name including discriminator or Discord account ID."
  
  if "has:" in parsed and parsed["has:"] not in ["link", "embed", "file"]:
    return "Invalid search operator. Value of `has:` must be `link`, `embed`, or `file`."
  
  if "pinned:" in parsed and parsed["pinned:"] not in ["True", "False"]:
    return "Invalid search operator. Value of `pinned:` must be `True` or `False`."
  
  if "before:" in parsed:
    #Regex pattern = NNNN-NN-NN
    if re.match(r"\d{4}-\d{2}-\d{2}", parsed["before:"]):
      try:
        #Check if date is valid datetime object matching YYYY-MM-DD format
        datetime.datetime.strptime(parsed["before:"], "%Y-%m-%d")
      except ValueError:
        return "Invalid search operator. Value of `before:` must be valid date following `YYYY-MM-DD` format."
    else:
      return "Invalid search operator. Value of `before:` must be valid date following `YYYY-MM-DD` format."
  
  if "during:" in parsed:
    #See comments under "before:" for explanation
    if re.match(r"\d{4}-\d{2}-\d{2}", parsed["during:"]):
      try:
        datetime.datetime.strptime(parsed["during:"], "%Y-%m-%d")
      except ValueError:
        return "Invalid search operator. Value of `during:` must be valid date following `YYYY-MM-DD` format."
    else:
      return "Invalid search operator. Value of `during:` must be valid date following `YYYY-MM-DD` format."
  
  if "after:" in parsed:
    #See comments under "before:" for explanation
    if re.match(r"\d{4}-\d{2}-\d{2}", parsed["after:"]):
      try:
        datetime.datetime.strptime(parsed["after:"], "%Y-%m-%d")
      except ValueError:
        return "Invalid search operator. Value of `after:` must be valid date following `YYYY-MM-DD` format."
    else:
      return "Invalid search operator. Value of `after:` must be valid date following `YYYY-MM-DD` format."
  
  if "daterange:" in parsed:
    #Regex pattern = NNNN-NN-NN..NNNN-NN-NN
    if re.match(r"\d{4}-\d{2}-\d{2}\.\.\d{4}-\d{2}-\d{2}", parsed["daterange:"]):
      dates = parsed["daterange:"].split("..")
      try:
        #Check if both dates are valid datetime object matching YYYY-MM-DD format
        datetime.datetime.strptime(dates[0], "%Y-%m-%d")
        datetime.datetime.strptime(dates[1], "%Y-%m-%d")
      except ValueError:
        return "Invalid search operator. Value of `daterange:` must be 2 valid dates separated by `..` following `YYYY-MM-DD` format."
    else:
      return "Invalid search operator. Value of `daterange:` must be 2 valid dates separated by `..` following `YYYY-MM-DD` format."
  
  #Default return is empty string, all checks passed with no validation errors
  return ""

async def messageisvalid(msg, parsed):#, img = False):
  #if img:
  #  for a in msg.attachments:
  #    #Get fp object for each file attachment for Pillow to open
  #    f = await a.to_file()
  #    f = f.fp
  #    icontent = pytesseract.image_to_string(PIL.Image.open(f)).lower()
  #else:
  icontent = msg.content
  
  for l in parsed["exact"]:
    if l not in icontent:
      return False
  
  for l in parsed["any"]:
    #Take each list in anylist, if at least 1 entry in each list is in msg.content case insensitive, then msg is a match
    if all(str(either).lower() not in icontent.lower() for either in l):
      return False
  
  if "without" in parsed:
    for word in parsed["without"]:
      if word.lower() in icontent.lower():
        return False
  
  if "from:" in parsed:
    #Value of from: can be string of numbers representing sender ID or string ending with #NNNN representing sender name + discriminator
    if parsed["from:"] != str(msg.author.id) and parsed["from:"] != (msg.author.name + "#" + msg.author.discriminator):
      return False
  
  if "mentions:" in parsed:
    if all(m not in "".join(str(msg.mentions)) for m in parsed["mentions:"].split("#")):
      return False
  
  if "has:" in parsed: #Regex URL search created by Allan on stackoverflow, pretty much gets any valid link as match
    if parsed["has:"] == "link" and re.search(r"\b((?:https?://)?(?:(?:www\.)?(?:[\da-z\.-]+)\.(?:[a-z]{2,6})|(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)|(?:(?:[0-9a-fA-F]{1,4}:){7,7}[0-9a-fA-F]{1,4}|(?:[0-9a-fA-F]{1,4}:){1,7}:|(?:[0-9a-fA-F]{1,4}:){1,6}:[0-9a-fA-F]{1,4}|(?:[0-9a-fA-F]{1,4}:){1,5}(?::[0-9a-fA-F]{1,4}){1,2}|(?:[0-9a-fA-F]{1,4}:){1,4}(?::[0-9a-fA-F]{1,4}){1,3}|(?:[0-9a-fA-F]{1,4}:){1,3}(?::[0-9a-fA-F]{1,4}){1,4}|(?:[0-9a-fA-F]{1,4}:){1,2}(?::[0-9a-fA-F]{1,4}){1,5}|[0-9a-fA-F]{1,4}:(?:(?::[0-9a-fA-F]{1,4}){1,6})|:(?:(?::[0-9a-fA-F]{1,4}){1,7}|:)|fe80:(?::[0-9a-fA-F]{0,4}){0,4}%[0-9a-zA-Z]{1,}|::(?:ffff(?::0{1,4}){0,1}:){0,1}(?:(?:25[0-5]|(?:2[0-4]|1{0,1}[0-9]){0,1}[0-9])\.){3,3}(?:25[0-5]|(?:2[0-4]|1{0,1}[0-9]){0,1}[0-9])|(?:[0-9a-fA-F]{1,4}:){1,4}:(?:(?:25[0-5]|(?:2[0-4]|1{0,1}[0-9]){0,1}[0-9])\.){3,3}(?:25[0-5]|(?:2[0-4]|1{0,1}[0-9]){0,1}[0-9])))(?::[0-9]{1,4}|[1-5][0-9]{4}|6[0-4][0-9]{3}|65[0-4][0-9]{2}|655[0-2][0-9]|6553[0-5])?(?:/[\w\.-]*)*/?)\b", icontent) == None:
      return False
    if parsed["has:"] == "embed" and len(msg.embeds) == 0:
      return False
    if parsed["has:"] == "file" and len(msg.attachments) == 0:
      return False
  
  if "before:" in parsed:
    if parsed["before:"] < str(msg.created_at):
      return False
  
  if "during:" in parsed:
    #msg.created_at same day; hrs, mins, and secs don't matter
    if parsed["during:"] != str(msg.created_at)[:10]:
      return False
  
  if "after:" in parsed:
    if parsed["after:"] >= str(msg.created_at):
      return False
  
  if "pinned:" in parsed:
    if parsed["pinned:"] != str(msg.pinned):
      return False
  
  if "filetype:" in parsed:
    if len(msg.attachments) == 0:
      return False
    for file in msg.attachments:
      if parsed["filetype:"] not in file.filename:
        return False
  
  if "daterange:" in parsed:
    #Check lower..higher and higher..lower date ranges
    if parsed["daterange:"][:10] < parsed["daterange:"][12:]:
      if str(msg.created_at)[:10] < parsed["daterange:"][:10] or str(msg.created_at)[:10] > parsed["daterange:"][12:]:
        return False
    else:
      if str(msg.created_at)[:10] > parsed["daterange:"][:10] or str(msg.created_at)[:10] < parsed["daterange:"][12:]:
        return False
  
  for l in parsed["around"]:
    flag = False
    #if both AROUND(n) word1 and word2 are lists (n..n)
    if str(type(l[1])) == "<class 'list'>" and str(type(l[2])) == "<class 'list'>":
      #Check for each num around each num from other list
      for i in l[1]:
        for j in l[2]:
          #Regex pattern = word boundarys around first and second word, with up to N words between first and second word, case insensitive
          #N being l[0] proximity variable from messageParser()
          #Regex pattern searched twice with word1 and word2 swapped so either word can be around the other
          if re.search(r"\b" + str(i) + r"\W+(?:\w+\W+){0," + l[0] + r"}?" + str(j) + r"\b", icontent, flags = re.I) != None or re.search(r"\b" + str(j) + r"\W+(?:\w+\W+){0," + l[0] + r"}?" + str(i) + r"\b", icontent, flags = re.I) != None:
            flag = True
      #flag will be False if all combinations of i around j and j around i are False
      if flag == False:
        return False
    #if only word1 is list (n..n)
    elif str(type(l[1])) == "<class 'list'>":
      for i in l[1]:
        if re.search(r"\b" + str(i) + r"\W+(?:\w+\W+){0," + l[0] + r"}?" + l[2] + r"\b", icontent, flags = re.I) != None or re.search(r"\b" + l[2] + r"\W+(?:\w+\W+){0," + l[0] + r"}?" + str(i) + r"\b", icontent, flags = re.I) != None:
          flag = True
      if flag == False:
        return False
    #if only word2 is list (n..n)
    elif str(type(l[2])) == "<class 'list'>":
      for i in l[2]:
        if re.search(r"\b" + str(i) + r"\W+(?:\w+\W+){0," + l[0] + r"}?" + l[1] + r"\b", icontent, flags = re.I) != None or re.search(r"\b" + l[1] + r"\W+(?:\w+\W+){0," + l[0] + r"}?" + str(i) + r"\b", icontent, flags = re.I) != None:
          flag = True
      if flag == False:
        return False
    else:
      #Neither word1 nor word2 are lists, search with same pattern without looping
      if re.search(r"\b" + l[1] + r"\W+(?:\w+\W+){0," + l[0] + r"}?" + l[2] + r"\b", icontent, flags = re.I) == None and re.search(r"\b" + l[2] + r"\W+(?:\w+\W+){0," + l[0] + r"}?" + l[1] + r"\b", icontent, flags = re.I) == None:
        return False
  
  for c in ["s!help", "s!search ", "s!showall ", "s!oldest ", "s!relevent ", "s!exact ", "s!regex ", "s!image "]:
    if icontent.startswith(c):
      #Don't return any messages with SearchBot commands, gives cleaner results since you don't have to worry about other people's searches being in your own search results
      return False
  
  if msg.author == client.user:
    return False
  
  if all(words in icontent.lower() for words in parsed["content"].lower().split()) == False:
      return False
  
  #Default return value True, msg passed all checks and will be included in list given to Display()
  return True

async def display(result, channel, showall = False):
  retstr = ""
  messages = []
  count = 0 #Total messages found
  dis = 0 #Amt of messages displayed, not used if showall passed as True
  
  for i in result:
    flag = False
    #Messages displayed as follows:
    #```content```
    #jump_url
    #Check if adding next message would push retstr past Discord char limit for single message
    if len(retstr + "```" + i.content + "```" + i.jump_url + "\n\n") > 2000 or len(retstr + "``` ```" + i.jump_url + "\n\n") > 2000:
      messages.append(retstr)
      retstr = ""
    #Check if message itself is over char limit
    if len("```" + i.content + "```" + i.jump_url) > 2000:
      #Append message up to char limit ending with ... after cutoff
      messages.append("```" + i.content[:(2000 - len(i.jump_url) - 9)] + "...```" + i.jump_url)
      flag = True
    #Check if message is empty (will happen if message is image embed, etc)
    if len(i.content) == 0:
      retstr = retstr + "``` ```" + i.jump_url + "\n\n"
      flag = True
    if flag == False:
      retstr = retstr + "```" + i.content + "```" + i.jump_url + "\n\n"
    count = count + 1
    #Stop adding to dis when over 5 messages to send
    if len(messages) < 6:
      dis = count
  messages.append(retstr)
  
  if messages[0] == "":
    await channel.send("No search results found.")
  else:
    if showall:
      await channel.send("Showing " + str(count) + " results found.")
      for msg in messages:
        if len(msg) > 0:
          await channel.send(msg)
    else:
      await channel.send("Showing " + str(dis) + " of " + str(count) + " results found.")
      cnt = 0
      #Send first up to 5 messages
      while cnt < 5 and cnt < len(messages):
        if len(messages[cnt]) > 0:
          await channel.send(messages[cnt])
          cnt = cnt + 1

ping()
try:
  #Starts the bot
  #TOKEN environment variable needs to be set with discord bot token
  client.run(os.environ["TOKEN"])
except Exception as e:
  print(str(e.code))
  print(e.text)