# -*- coding: utf-8 -*-
"""Predicates for authorizations"""
from tg.predicates import Predicate
from pod.model import DBSession as session
from pod.model.auth import Permission, User
import logging as l

DIRTY_canReadOrCanWriteSqlQuery = """
SELECT
    pgn.node_id
FROM
    pod_group_node AS pgn
    JOIN pod_nodes AS pn ON pn.node_id = pgn.node_id AND pn.is_shared = 't'
    JOIN pod_user_group AS pug ON pug.group_id = pgn.group_id
    JOIN pod_user AS pu ON pug.user_id = pu.user_id
WHERE
    rights > :excluded_right_low_level
    AND email_address = :email
    AND pgn.node_id = :node_id
UNION
    SELECT
        pnn.node_id
    FROM
        pod_nodes AS pnn,
        pod_user AS puu
    WHERE
        pnn.node_id = :node_id
        AND pnn.owner_id = puu.user_id
        AND puu.email_address = :email
"""

class can_read(Predicate):
    message = ""

    def __init__(self, **kwargs):
        pass

    def evaluate(self, environ, credentials):
        if 'node_id' in environ['webob.adhoc_attrs']['validation']['values']:
            node_id = environ['webob.adhoc_attrs']['validation']['values']['node_id']
            if node_id!=0:
                has_right = session.execute(
                    DIRTY_canReadOrCanWriteSqlQuery,
                    {"email":credentials["repoze.who.userid"], "node_id":node_id, "excluded_right_low_level": 0}
                )
                if has_right.rowcount == 0 :
                    l.info("User {} don't have read right on node {}".format(credentials["repoze.who.userid"], node_id))
                    self.unmet()

class can_write(Predicate):
    message = ""

    def __init__(self, **kwargs):
        pass

    def evaluate(self, environ, credentials):
        node_id = environ['webob.adhoc_attrs']['validation']['values']['node_id']
        if node_id!=0:
            has_right = session.execute(
                DIRTY_canReadOrCanWriteSqlQuery,
                {"email":credentials["repoze.who.userid"], "node_id":node_id, "excluded_right_low_level": 1}
            )
            if has_right.rowcount == 0 :
                self.unmet()
