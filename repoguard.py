#!/usr/bin/env python
# -*- coding: utf-8 -*-
import yaml
import re
import os
import subprocess
import datetime
import arrow
import argparse
import logging
import sys

from core.git_repo_updater import GitRepoUpdater
from core.codechecker import CodeCheckerFactory, Alert
from core.ruleparser import build_resolved_ruleset, load_rules
from core.notifier import EmailNotifier, EmailNotifierException
from core.repository_handler import RepositoryHandler, RepositoryException
from core.datastore import  DataStore, DataStoreException

class RepoGuard:
    def __init__(self):
        self.CONFIG = {}
        self.repo_list = {}
        self.repo_status = {}
        self.repo_status_new = {}
        self.check_results = []

        self.logger = logging.getLogger()
        # create formatter and add it to the handlers
        formatter = logging.Formatter('%(asctime)s %(processName)-10s %(name)s %(levelname)-8s %(message)s')
        # create console handler with a higher log level
        ch = logging.StreamHandler()
        ch.setFormatter(formatter)
        # Setup logger output
        self.logger.addHandler(ch)

        self.parse_args()
        self.detect_paths()

    def parse_args(self):
        parser = argparse.ArgumentParser(description='Watch git repos for changes...')
        parser.add_argument('--config', '-c', default='etc/config.yml', help='Path to the config.yml file')
        parser.add_argument('--rule-dir', default='rules/', help='Path to the rule directory')
        parser.add_argument('--working-dir', default='../repos/', help='Path to the rule directory')
        parser.add_argument('--since', '-s', default=False,
                            help='Search for alerts in older git commits (git rev-list since, e.g. 2013-05-05 01:00)')
        parser.add_argument('--refresh', '-r', action='store_true', default=False,
                            help='Refresh repo list and locally stored repos from github api')
        parser.add_argument('--limit', '-l', default=False,
                            help='Limit checks only to run on the given repos (comma separated list)')
        parser.add_argument('--alerts', '-a', default=False,
                            help='Limit running only the given alert checks (comma separated list)')
        parser.add_argument('--nopull', action='store_true', default=False, help='No repo pull if set')
        parser.add_argument('--notify', '-N', action='store_true', default=False,
                            help='Notify pre-defined contacts via e-mail')
        parser.add_argument('--silent', action="count", help='Supress log messages lower than warning')
        parser.add_argument('--store', '-S', default=False, help='ElasticSearch node (host:port)')
        parser.add_argument('--ignorestatus', action='store_true', default=False,
                            help='If true repoguard will not skip commits which are were already '
                                 'checked based on the status file')

        self.args = parser.parse_args()

        # if self.args.rule_dirs:
        #     self.args.rule_dirs = self.args.rule_dirs.split(',')
        if self.args.limit:
            self.args.limit = self.args.limit.split(',')
        if self.args.alerts:
            self.args.alerts = self.args.alerts.split(',')

        if self.args.silent:
            self.logger.setLevel(logging.WARNING)
        else:
            self.logger.setLevel(logging.DEBUG)

    def detect_paths(self):
        self.APP_DIR = '%s/' % os.path.abspath(os.path.join(__file__, os.pardir, os.pardir))
        self.CONFIG_PATH = self.args.config
        self.WORKING_DIR = self.args.working_dir
        self.ALERT_CONFIG_DIR = self.args.rule_dir

    def read_config(self, path):
        try:
            with open(path) as f:
                config = yaml.load(f.read())
                self.skip_repo_list = config['skip_repo_list']
                self.default_notification_src_address = config['default_notification_src_address']
                self.default_notification_to_address = config['default_notification_to_address']
                self.subscribers = config['subscribers']
                self.org_name = config['github']['organization_name']
                self.github_token = config['github']['token']
                self.smtp_host = config['smtp']['host']
                self.smtp_port = config['smtp']['port']
                self.smtp_conn_string = self.smtp_host + ":" + str(self.smtp_port)
                self.smtp_username = config['smtp']['username']
                self.smtp_password = config['smtp']['password']
                self.use_tls = config['smtp']['use_tls']
                self.detect_rename = config['git']['detect_rename']
                self.debug = config['debug']
                self.notifications = config['notifications']
        except KeyError as e:
            print '%s not found in config file' % e
            sys.exit()
        except yaml.YAMLError, e:
            print "Error loading config file: %s\n" % path
            self.logger.exception("YAML Error while loading configuration file: " + e.message)
            sys.exit()
        except IOError, e:
            print "Error loading config file: %s\n" % path
            self.logger.exception("IO Error loading configuration file:" + e.strerror)
            sys.exit()

    def should_skip_by_name(self, repo_name):
        if self.args.limit:
            if repo_name not in self.args.limit:
                return True

        return repo_name in self.skip_repo_list

    def set_up_repository_handler(self):
        self.repository_handler = RepositoryHandler(self.WORKING_DIR)
        if not self.args.since:
            self.repository_handler.load_status_info_from_file()

    def update_local_repos(self):
        existing_repo_dirs = os.listdir(self.WORKING_DIR)

        repo_list = list(self.repository_handler.get_repo_list())
        for idx, repo in enumerate(repo_list):
            self.logger.debug('Pulling repo "%s/%s" (%d/%d) %2.2f%%' % (self.org_name, repo.name, idx, len(repo_list),
                                                                        float(idx) * 100 / len(repo_list)))

            if self.should_skip_by_name(repo.name):
                if self.debug:
                    self.logger.debug('Got --limit param and repo (%s) is not among them, skipping git pull/clone.'
                                      % repo.name)
                continue

            if repo.dir_name in existing_repo_dirs:
                repo.git_reset_to_oldest_hash()
                repo.call_command("git pull")
            else:
                repo.git_clone()
                repo.detect_new_commit_hashes()

    def check_new_code(self, detect_rename=False):
        existing_repo_dirs = os.listdir(self.WORKING_DIR)

        repo_list = list(self.repository_handler.get_repo_list())
        for idx, repo in enumerate(repo_list):
            self.logger.debug('Checking repo "%s/%s" (%d/%d) %2.2f%%' % (self.org_name, repo.name, idx, len(repo_list),
                                                                         float(idx) * 100 / len(repo_list)))
            if self.should_skip_by_name(repo.name):
                if self.debug:
                    self.logger.debug('Skipping code check for %s' % repo.name)
                continue
            if self.args.limit and repo.name not in self.args.limit:
                self.logger.debug('repo %s skipped because of --limit argument' % repo.name)
                continue
            if repo.dir_name in existing_repo_dirs:
                self.check_results += self.check_by_repo(repo, detect_rename=detect_rename)
            else:
                self.logger.debug('skip repo %s because directory doesnt exist' % repo.dir_name)

        # print self.checkResults
        # email notification is disabled, print to stdout
        if not self.args.notify:
            for alert in self.check_results:
                try:
                    print '\t'.join([
                        alert.rule.name, alert.repo, alert.commit, alert.filename, alert.rule.description,
                        alert.line[0:200].replace("\t", " ").decode('utf-8', 'replace')
                    ])
                except UnicodeEncodeError:
                    self.logger.exception('failed to get the details due to some unicode error madness')

    def store_results(self):
        (host, port) = self.args.store.split(":")
        data_store = DataStore(host=host, port=port)

        for alert in self.check_results:
            try:
                body = {
                    "check_id": alert.rule.name,
                    "description": alert.rule.description,
                    "filename": alert.filename,
                    "commit_id": alert.commit,
                    "matching_line": alert.line[0:200].replace("\t", " ").decode('utf-8', 'replace'),
                    "repo_name": alert.repo,
                    "@timestamp": datetime.datetime.utcnow().isoformat(),
                    "type": "repoguard",
                    "false_positive": False,
                    "last_reviewer": "repoguard"
                }

                data_store.store(body=body, index='repoguard', doc_type='repoguard')
            except DataStoreException:
                self.logger.exception('Got exception during storing results to ES.')

    # TODO: test
    def send_results(self):
        alert_per_notify_person = {}
        if not self.check_results:
            return False

        def add_alert(email):
            if email not in alert_per_notify_person:
                alert_per_notify_person[email] = "The following change(s) might introduce new security risks:\n\n"
            alert_per_notify_person[email] += alert

        self.logger.info('### SENDING NOTIFICATION EMAIL ###')

        for alert in self.check_results:
            check_id = alert.rule.name
            filename = alert.filename
            commit_id = alert.commit
            matching_line = alert.line[0:200].replace("\t", " ").decode('utf-8', 'replace')
            repo_name = alert.repo
            description = alert.rule.description

            alert = (u"check_id: %s \n"
                     "path: %s \n"
                     "commit: https://github.com/%s/%s/commit/%s\n"
                     "matching line: %s\n"
                     "description: %s\n"
                     "repo name: %s\n\n" % (check_id, filename, self.org_name, repo_name,
                                            commit_id, matching_line, description, repo_name))

            notify_users = self.find_subscribed_users(check_id)
            self.logger.debug('notify_users %s' % repr(notify_users))
            for u in notify_users:
                add_alert(u)

            # no subscribed email, send it to default address
            if not notify_users:
                add_alert(self.default_notification_to_address)

        from_addr = self.default_notification_src_address
        self.logger.debug('Notifiying them: %s', repr(alert_per_notify_person))
        for to_addr, text in alert_per_notify_person.iteritems():
            email_notification = EmailNotifier.create_notification(from_addr, to_addr, text, self.smtp_conn_string,
                                                                   self.smtp_username,
                                                                   self.smtp_password, self.use_tls)
            try:
                email_notification.send_if_fine()
            except EmailNotifierException, e:
                self.logger.exception("Error while sending email: " + str(e))

    def find_subscribed_users(self, alert):
        import fnmatch
        import itertools
        matching_subscriptions = [users for pattern, users in self.subscribers.iteritems()
                                  if fnmatch.fnmatch(alert, pattern)]
        return set(itertools.chain(*matching_subscriptions))

    def check_by_repo(self, repo, detect_rename=False):
        repo_id = repo.repo_id
        repo_name = repo.name
        cwd = repo.full_dir_path
        matches_in_repo = []

        if self.args.since:
            rev_list_to_check = repo.get_rev_list_since_date(self.args.since)
        else:
            if self.args.ignorestatus:
                rev_list_to_check = repo.get_last_commit_hashes()
            else:
                repo.detect_new_commit_hashes()
                rev_list_to_check = repo.get_not_checked_commit_hashes()

        for rev_hash in rev_list_to_check:
            repo.add_commit_hash_to_checked(rev_hash)
            rev_result = self.check_by_rev_hash(rev_hash, repo, detect_rename)
            if rev_result:
                matches_in_repo = matches_in_repo + rev_result
        if len(rev_list_to_check) > 0:
            self.logger.info("checked commits %s %s" % (repo_name, len(rev_list_to_check)))

        return matches_in_repo

    def check_by_rev_hash(self, rev_hash, repo, detect_rename=False):
        matches_in_rev = []
        cmd = "git show --function-context %s%s" % ('-M100% ' if detect_rename else '--no-renames ', rev_hash)

        try:
            diff_output = subprocess.check_output(cmd.split(), cwd=repo.full_dir_path)
            splitted = re.split(r'^diff --git a/\S* b/(\S+)$', diff_output, flags=re.MULTILINE)[1:]

            for i in xrange(len(splitted) / 2):
                filename = splitted[i * 2]
                diff = splitted[i * 2 + 1]

                result = self.code_checker.check(diff.split('\n'), filename)
                alerts = [Alert(rule, filename, repo.name, rev_hash, line) for rule, line in result]

                matches_in_rev.extend(alerts)
        except subprocess.CalledProcessError as e:
            self.logger.exception('Failed running: %s' % cmd)

        return matches_in_rev

    def read_alert_config_from_file(self):
        bare_rules = load_rules(self.ALERT_CONFIG_DIR)
        resolved_rules = build_resolved_ruleset(bare_rules)

        # filter for items in --alerts parameter
        applied_alerts = {aid: adata for aid, adata in resolved_rules.iteritems()
                          if not self.args.alerts or aid in self.args.alerts}

        self.logger.debug('applied_alerts: %s' % repr(applied_alerts))
        self.code_checker = CodeCheckerFactory(applied_alerts).create()

    def put_lock(self):
        lockfile = open(self.APP_DIR + "repoguard.pid", "w")
        lockfile.write(str(os.getpid()))
        lockfile.close()

    def release_lock(self):
        os.remove(self.APP_DIR + "repoguard.pid")

    def is_locked(self):
        if os.path.isfile(self.APP_DIR + "repoguard.pid"):
            lockfile = open(self.APP_DIR + "repoguard.pid", "r")
            pid = lockfile.readline().strip()
            lockfile.close()

            if os.path.exists("/proc/%s" % pid):
                return True
            else:
                self.logger.error('Lock there but script not running, removing lock entering aborted state...')
                if self.notifications:
                    email_notification = EmailNotifier(
                        self.default_notification_src_address,
                        self.default_notification_to_address,
                        "[repoguard] invalid lock, entering aborted state",
                        "Found lock with PID %s, but process not found... "
                        "entering aborted state (someone should check the logs and restart manually!)")

                    email_notification.send_if_fine()

                self.release_lock()
                self.set_aborted()
                return False
        else:
            self.logger.debug("pid file not found, not locked...")
            return False

    def set_aborted(self):
        aborted_state_file = open(self.WORKING_DIR + "aborted_state.lock", "w")
        aborted_state_file.write('1')
        aborted_state_file.close()

    def is_aborted(self):
        return os.path.isfile(self.WORKING_DIR + 'aborted_state.lock')

    def run(self):
        self.logger.info('* run started')
        self.read_config(self.CONFIG_PATH)
        self.read_alert_config_from_file()

        # locking
        if self.is_aborted() and self.debug:
            self.logger.info('Aborted state, quiting!')
            return

        if self.is_locked():
            self.logger.info('Locked, script running... waiting.')
            return

        self.put_lock()

        self.set_up_repository_handler()

        if self.args.refresh or not self.repository_handler.get_repo_list():
            git_repo_updater_obj = GitRepoUpdater(self.org_name, self.github_token,
                                                  self.repository_handler.repo_list_file, self.logger)
            git_repo_updater_obj.refresh_repo_list()
            git_repo_updater_obj.write_repo_list_to_file()

        if not self.args.nopull:
            self.update_local_repos()

        self.check_new_code(self.detect_rename)

        if self.args.notify:
            pass
            # self.send_results()

        if self.args.store:
            self.store_results()

        if not self.args.since:
            self.repository_handler.save_repo_status_to_file()
        self.release_lock()
        self.logger.info("* run finished")


if __name__ == '__main__':
    RepoGuard().run()
