# Discord bot implementing a better way to search.

Needs optimization before release.

## Commands list:
``!help``: Shows list of commands and operators.

``s!search``: Results contain search message within contents, sorted from newest to oldest.

``s!showall``: Same results as ``s!search`` but displays every message found. Not recommended for broad searches in servers with high message counts.

``s!oldest``: Same results as ``s!search`` but in reverse order, displayed from oldest to most recent.

``s!relevent``: Sorts results by frequency of search term appearances within the contents of the results.

``s!exact``: Shows messages where the entire content of the message is exactly the message being searched, results are case sensitive. Search operators cannot be used with ``s!exact``.

``s!regex``: Assumes search to be using regular expressions as search operators. Other search operators cannot be used with ``s!regex``.

``s!image``: Results contain search message within any attached image, using artificial intelligence to read any text within the image. This uses an implementation of Google's Tesseract OCR, and results may not be entirely accurate.


All commands with exception to ``s!oldest`` and ``s!relevent`` sort results from most recent to oldest. All commands with exception to ``s!showall`` display only the first 10,000 characters of results as to not flood the channel with messages. Searching works by checking whether every message contains each word being searched within its contents, not necessarily in order and not necessarily case sensitive, with exception to ``s!exact`` and ``s!regex``. Discord's integrated search functions are usable, as well as more advanced search operators used in other search engines.

## A list of search operators and what they do below:

``from:``user: Results only include messages sent by the specified user. Discord tag or User ID required.

``mentions:``user: Results only include messages that tag the specified user. Discord tag or User ID required.

``has:``link OR embed OR file: Results only include messages that contain a link, an embed, or a file attached.

``before:``date: Results only include messages sent before specified date, in ``YYYY-MM-DD`` format.

``during:``date: Results only include messages sent during specified date, in ``YYYY-MM-DD`` format.

``after:``date: Results only include messages sent after specified date, in ``YYYY-MM-DD`` format.

``in:``channel: Results only include messages sent in specified channel.

``pinned:``True OR False: Results only include messages that are / aren't pinned.

``filetype:``file extension: Results only include messages with attatchment of specified file extension.

``daterange:``date..date: Results only include messages sent between the two dates specified, in ``YYYY-MM-DD..YYYY-MM-DD`` format.

``limit:n``: Speeds up search by limiting the number of messages searched to ``n`` newest messages. If using ``s!oldest`` with ``limit:``, results will show the oldest messages within the most recent ``n`` messages, not the ``n`` oldest messages. Using ``limit:`` is highly recommended for servers with high message counts.


``" "`` / ``+``: Everything within quotation marks or after a plus sign will be taken as exact, results are case sensitive.

``OR`` / ``|``: Shows results which match with either the word directly before or after the operator (note: due to implementation, ``OR`` operator will not work with Discord operators or ``AROUND(n)`` / ``near(n)`` operator).

``AROUND(n)`` / ``near(n)``: Results only include messages where the words directly before and after the operator are no more than ``n`` words apart.

``..``: If used between two different numbers, results will include any number within the range of the two numbers, inclusive.

``-``: Removes results containing everything after the hypen.
