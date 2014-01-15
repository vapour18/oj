#Create your views here.
# -.- encoding: utf-8 -.-

from Problem.models import Problem
from User.models import User
from django.http import HttpResponse
from hashlib import md5
from django.shortcuts import render_to_response, render, redirect
from kari.const import Const
from Problem.forms import addProblemForm
from django.core.files.storage import default_storage
from Contest.models import ContestProblem, Contest
from Statistic.models import Board
from Statistic.utils import *
from Submission.models import Submission, GeneralSubmission
from common.err import Err
from datetime import datetime
import os
import json
import math
import copy
import logging

logger = logging.getLogger('django')

def showBoardByStatus(request, cId):
    logger.info(str(request).replace("\n","\t"))
    try:
        u = User.getSessionUser(request.session)
        if not u:
            raise Err(request, 'not login')
        try:
            cId = int(cId)
            c = Contest.getById(cId)
        except:
            raise Err(request, 'no resource')

        can_manage = True
        try:
            c.canBeManaged(u)
        except:
            can_manage = False

        try:
            c.canEnterContest(u)
        except:
            raise Err(request, 'no priv')

        allSub = Submission.submissionList(c=c).order_by('sid')
        allUser = c.course_class.getAllStudents()
        allProb = c.getContestProblem()
        
        pInfoDict = {pinfo.problem_index:{'idx':pinfo.problem_index,'ac':0,'pen':0,'sub':0} for pinfo in allProb}
        info = {uinfo.uid:{
            'uid':uinfo.uid,
            'username':uinfo.username,
            'nickname':uinfo.nickname,
            'ac':0,'pen':0,
            'pinfo':copy.deepcopy(pInfoDict)
            } for uinfo in allUser}

        if c.board_type == 0:  # acm style board
            for sinfo in allSub:
                if not sinfo.user.uid in info:
                    continue
                uid = sinfo.user.uid
                idx = sinfo.problem_index.problem_index
                if info[uid]['pinfo'][idx]['ac'] > 0:
                    continue
                if sinfo.status in ['Pending', 'Rejudging', 'Compiling', 'System Error']:
                    continue
                td = sinfo.submission_time-c.start_time
                info[uid]['pinfo'][idx]['sub']+=1
                if sinfo.status == "Accepted":
                    info[uid]['pinfo'][idx]["ac"]=1-info[uid]['pinfo'][idx]["ac"]
                    info[uid]['pinfo'][idx]["ac_time"]=int(math.ceil(td.total_seconds()/60))
                    info[uid]['pinfo'][idx]["pen"]+=int(math.ceil(td.total_seconds()/60))
                    if (not 'fb_time' in pInfoDict[idx]) or td < pInfoDict[idx]['fb_time']:
                        pInfoDict[idx]['fb_time'] = td
                        pInfoDict[idx]['fb_uid'] = uid
                else:
                    info[uid]['pinfo'][idx]["ac"]-=1
                    info[uid]['pinfo'][idx]["pen"]+=20

            for idx, pinfo in pInfoDict.iteritems():
                if 'fb_time' in pinfo:
                    info[pinfo['fb_uid']]['pinfo'][idx]['fb'] = True

            info = info.values()
            for i in info:
                i['pinfo'] = i['pinfo'].values()
                i['pinfo'].sort(key=lambda x:x['idx'])
                for pinfo in i['pinfo']:
                    if pinfo['ac'] > 0:
                        i['ac'] += 1
                        i['pen'] += pinfo['pen']
        else:
            for sinfo in allSub:
                if not sinfo.user.uid in info:
                    continue
                uid = sinfo.user.uid
                idx = sinfo.problem_index.problem_index
                other_info = eval(sinfo.other_info)
                tscore = int(other_info['score'])

                if info[uid]['pinfo'][idx]['ac'] >= tscore:
                    continue
                if sinfo.status in ['Pending', 'Rejudging', 'Compiling', 'System Error']:
                    continue
                td = sinfo.submission_time-c.start_time
                info[uid]['pinfo'][idx]['sub']+=1
                info[uid]['pinfo'][idx]['ac']=tscore
                info[uid]['pinfo'][idx]["pen"]+=int(math.ceil(td.total_seconds()/60))-info[uid]['pinfo'][idx].get("ac_time",0)
                info[uid]['pinfo'][idx]["ac_time"]=int(math.ceil(td.total_seconds()/60))
                if sinfo.status == "Accepted":
                    if (not 'fb_time' in pInfoDict[idx]) or td < pInfoDict[idx]['fb_time']:
                        pInfoDict[idx]['fb_time'] = td
                        pInfoDict[idx]['fb_uid'] = uid

            for idx, pinfo in pInfoDict.iteritems():
                if 'fb_time' in pinfo:
                    info[pinfo['fb_uid']]['pinfo'][idx]['fb'] = True

            info = info.values()
            for i in info:
                i['pinfo'] = i['pinfo'].values()
                for pinfo in i['pinfo']:
                    if pinfo['ac'] > 0:
                        i['ac'] += pinfo['ac']
                        i['pen'] += pinfo['pen']


        info.sort(key=lambda x:x['ac']*262144-x['pen'], reverse=True)
        for r, i in enumerate(info, 1):
            i['rank'] = r

        if can_manage or c.contest_type==0:
            rank = info
        else:
            rank = filter(lambda x:u.uid==x['uid'], info)

        return render(request,"newtpl/statistic/board.html", {'info': info, 'rank': rank,'allProb': allProb, 'contest': c})
    except Exception as e:
        logger.error(str(e).replace("\n","\t"))
        return render(request, Err.ERROR_PAGE)

def showBoardByScore(request, cId):# modified
    logger.info(str(request).replace("\n","\t"))
    try:
        u = User.getSessionUser(request.session)
        if not u:
            raise Err(request, 'not login')
        try:
            cId = int(cId)
            c = Contest.getById(cId)
        except:
            raise Err(request, 'no resource')

        can_manage = True
        try:
            c.canBeManaged(u)
        except:
            can_manage = False

        try:
            c.canEnterContest(u)
        except:
            raise Err(request, 'no priv')

        allSub = Submission.submissionList(c=c).order_by('sid')
        allUser = c.course_class.getAllStudents()
        allProb = c.getContestProblem()

        pInfoDict = {pinfo.problem_index:{'ac':0,'pen':0,'sub':0} for pinfo in allProb}
        info = {uinfo.uid:{
            'uid':uinfo.uid,
            'username':uinfo.username,
            'nickname':uinfo.nickname,
            'ac':0,'pen':0,
            'pinfo':copy.deepcopy(pInfoDict)
            } for uinfo in allUser}

        for sinfo in allSub:
            if not sinfo.user.uid in info:
                continue
            uid = sinfo.user.uid
            idx = sinfo.problem_index.problem_index
            other_info = eval(sinfo.other_info)
            tscore = int(other_info['score'])

            if info[uid]['pinfo'][idx]['ac'] >= tscore:
                continue
            if sinfo.status in ['Pending', 'Rejudging', 'Compiling', 'System Error']:
                continue
            td = sinfo.submission_time-c.start_time
            info[uid]['pinfo'][idx]['sub']+=1
            info[uid]['pinfo'][idx]['ac']=tscore
            info[uid]['pinfo'][idx]["pen"]+=int(math.ceil(td.total_seconds()/60))-info[uid]['pinfo'][idx].get("ac_time",0)
            info[uid]['pinfo'][idx]["ac_time"]=int(math.ceil(td.total_seconds()/60))
            if sinfo.status == "Accepted":
                if (not 'fb_time' in pInfoDict[idx]) or td < pInfoDict[idx]['fb_time']:
                    pInfoDict[idx]['fb_time'] = td
                    pInfoDict[idx]['fb_uid'] = uid

        for idx, pinfo in pInfoDict.iteritems():
            if 'fb_time' in pinfo:
                info[pinfo['fb_uid']]['pinfo'][idx]['fb'] = True

        info = info.values()
        for i in info:
            i['pinfo'] = i['pinfo'].values()
            for pinfo in i['pinfo']:
                if pinfo['ac'] > 0:
                    i['ac'] += pinfo['ac']
                    i['pen'] += pinfo['pen']

        info.sort(key=lambda x:x['ac']*262144-x['pen'], reverse=True)
        for r, i in enumerate(info, 1):
            i['rank'] = r

        if can_manage or c.contest_type==0:
            rank = info
        else:
            rank = filter(lambda x:u.uid==x['uid'], info)

        return render(request,"newtpl/statistic/board.html", {'info': info, 'rank': rank,'allProb': allProb, 'contest': c})
    except Exception as e:
        logger.error(str(e).replace("\n","\t"))
        return render(request, Err.ERROR_PAGE)

def showContestProblemStatistics( request, p_index=None, cid=None):
    logger.info(str(request).replace("\n","\t"))
    """
    view used to show statistics of a problem in a contest
    """
    try:
        u = User.getSessionUser(request.session)
        if not u:
            raise Err( request, err='not login')

        cid = int(cid)
        c = Contest.getById(cid)

        p_index = p_index if p_index else ''

        try:
            contest_problem = ContestProblem.getBy( c, p_index)
        except:
            raise Err( request, err='no contestproblem', 
                    log_format=( '{0}'.format(p_index), ''), 
                    user_format=( u'{0}'.format( p_index), u'搞错了什么吧！'),
                    )

        if not contest_problem.contest.course_class.canBeManaged( u):
            raise Err( request, err = 'no priv')

        all_submissions = Submission.submissionList( cp=contest_problem )
        submissions = all_submissions.filter( status='Accepted').order_by('run_time')[:20]

        status_list = []
        for i in Const.STATUS_CN.iterkeys():
            status_list.append( { 'name': Const.STATUS_CN[i], 'number': all_submissions.filter( status=i).count()} )

        for sub_s in submissions:
            sub_s.status_color = Const.STATUS_COLOR[sub_s.status] if sub_s.status in Const.STATUS_COLOR else ''
            sub_s.status_cn = Const.STATUS_CN[ sub_s.status]

        return render( request, 'newtpl/statistic/contest_problem.html', { 'submissions': submissions, 'contest_problem': contest_problem, 'status_list': status_list, 'tpl': { 'sp': True } })

    except Exception as e:
        logger.error(str(e).replace("\n","\t"))
        return render(request, Err.ERROR_PAGE, { 'errmsg': unicode(e) } )

def showProblemStatistics( request, pid=None ):
    logger.info(str(request).replace("\n","\t"))
    """
    view used to show statistics of a problem
    """
    try:
        u = User.getSessionUser(request.session)
        if not u:
            raise Err( request, err='not login')

        pid = int( pid) if pid else ''

        try:
            problem = Problem.getById( pid)
        except:
            raise Err( request, err='no problem', 
                    log_format=( '{0}'.format( pid), ''), 
                    user_format=( u'{0}'.format( pid), u'搞错了什么吧！'),
                    )

        # if not problem.contest.course_class.canBeManaged( u):
            # raise Err( request, err = 'no priv')

        all_submissions = GeneralSubmission.generalSubmissionList( p=problem )
        submissions = all_submissions.filter( status='Accepted').order_by('run_time')[:20]

        status_list = []
        for i in Const.STATUS_CN.iterkeys():
            status_list.append( { 'name': Const.STATUS_CN[i], 'number': all_submissions.filter( status=i).count()} )

        for sub_s in submissions:
            sub_s.status_color = Const.STATUS_COLOR[sub_s.status] if sub_s.status in Const.STATUS_COLOR else ''
            sub_s.status_cn = Const.STATUS_CN[ sub_s.status]

        # need modification
        return render( request, 'newtpl/statistic/problem.html', { 'submissions': submissions, 'problem': problem, 'status_list': status_list, 'tpl': { 'sp': True } })

    except Exception as e:
        logger.error(str(e).replace("\n","\t"))
        return render(request, Err.ERROR_PAGE, { 'errmsg': unicode(e) } )
