#!/usr/bin/env python

import datetime
import json
import os
import random
import subprocess
import time
import pdb


urnd = random.SystemRandom()


def urandom_int():
    urandom = map(ord, os.urandom(4))
    offset = 0
    for d in range(4):
        offset += pow(urandom[d], 2**d)
    return offset


def random_offset(size):
    bigint = urandom_int()
    offset_range = bigint % size
    return offset_range - (size/2)


def random_timestamp():
    now_epoch = int(time.time())
    urandom = map(ord, os.urandom(4))
    offset = 0
    for d in range(4):
        offset += pow(urandom[d], 2**d)
    return now_epoch - (offset % 86400)


# python <2.7 monkey patch
if "check_output" not in dir( subprocess ):
    def f(*popenargs, **kwargs):
        if 'stdout' in kwargs:
            raise ValueError('stdout argument not allowed, it will be overridden.')
        process = subprocess.Popen(stdout=subprocess.PIPE, *popenargs, **kwargs)
        output, unused_err = process.communicate()
        retcode = process.poll()
        if retcode:
            cmd = kwargs.get("args")
            if cmd is None:
                cmd = popenargs[0]
            raise subprocess.CalledProcessError(retcode, cmd)
        return output
    subprocess.check_output = f


def run_command(cmd):
    return subprocess.check_output(cmd, shell=True)


def run_dash_cli_command(cmd):
    return run_command("%s %s" % ('dash-cli', cmd))


def get_votes():
    global max_percentage_len
    global max_needed_len
    global days_to_finalization
    global ballot_entries


    mncount = int(run_dash_cli_command('masternode count enabled'))
    block_height = int(run_dash_cli_command('getblockcount'))
    blocks_to_next_cycle = (16616 - (block_height % 16616))
    next_cycle_epoch = int(int(time.time()) + (157.5 * blocks_to_next_cycle))
    days_to_next_cycle = blocks_to_next_cycle / 576.0
    days_to_finalization = days_to_next_cycle - 3


    # get ballot
    ballots = json.loads(run_dash_cli_command('gobject list all'))
    ballot = {}

    for entry in ballots:

        # unescape data string
        ballots[entry]['_data'] = json.loads(ballots[entry][u'DataHex'].decode("hex"))

        (go_type, go_data) = ballots[entry]['_data'][0]
        ballots[entry][go_type] = go_data

        if str(go_type) == 'watchdog':
            continue

        if int(go_data["type"]) == 2:
            continue

        if int(go_data[u'end_epoch']) < int(time.time()):
            continue

        if (ballots[entry][u'NoCount'] - ballots[entry][u'YesCount']) > mncount/10:
            continue

        if int(go_data[u'end_epoch']) < next_cycle_epoch:
            continue

        ballots[entry][u'vote'] = 'SKIP'
        ballots[entry][u'votes'] = json.loads(run_dash_cli_command('gobject getvotes %s' % entry))

        ballot[entry] = ballots[entry]

    votecount = len(ballot)
    max_proposal_len = 0
    max_yeacount_len = 0
    max_naycount_len = 0
    max_percentage_len = 0
    max_needed_len = 0
    for entry in ballot:
        yeas = ballot[entry][u'YesCount']
        nays = ballot[entry][u'NoCount']
        name = ballot[entry]['proposal'][u'name']
        threshold = mncount/10
        percentage = "{0:.1f}".format(
            (float((yeas + nays)) / float(mncount)) * 100)
        votes_needed = (threshold) - (yeas - nays)
        ballot[entry][u'vote_turnout'] = percentage
        ballot[entry][u'total_votes'] = yeas + nays
        ballot[entry][u'votes_needed'] = votes_needed
        ballot[entry][u'vote_threshold'] = (
            yeas + nays) > threshold and True or False
        ballot[entry][u'vote_passing'] = (
            yeas - nays) > threshold and True or False
        ballot[entry][u'voted_down'] = (
            nays - yeas) > threshold and True or False
        max_proposal_len = max(
            max_proposal_len,
            len(name))
        max_needed_len = max(max_needed_len, len(str(votes_needed)))
        max_yeacount_len = max(max_yeacount_len, len(str(yeas)))
        max_naycount_len = max(max_naycount_len, len(str(nays)))
        max_percentage_len = max(max_percentage_len, len(str(percentage)))

    ballot_entries = sorted(ballot, key=lambda s: ballot[s]['votes_needed'], reverse=False)

    return ballot_entries

if __name__ == '__main__':
    get_votes()
    pdb.set_trace()

