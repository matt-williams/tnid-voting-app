import requests
import time
from gql import gql, Client
from gql.transport.aiohttp import AIOHTTPTransport

class Tnid:
    def __init__(self, client_id, client_secret):
        # Get a bearer token for use with the TNID API
        rsp = requests.post('https://api.staging.v2.tnid.com/auth/token',
                            headers={'Content-Type': 'application/x-www-form-urlencoded'},
                            data={'client_id': client_id, 'client_secret': client_secret})
        token = rsp.json().get('access_token')
        
        # Create a GraphQL client using this bearer token
        self.client = Client(transport=AIOHTTPTransport(url='https://api.staging.v2.tnid.com/company',
                                                        headers={'Authorization': f'Bearer {token}'}),
                             fetch_schema_from_transport=True)

    def users(self, telephone_number, limit=1):
        '''See https://docs.tnid.com/company/b2c-features/search-people'''
        return self.client.execute(gql(
            '''
            query (
                $name: String
                $email: String
                $telephoneNumber: String
                $limit: Int
              ) {
                users (
                name: $name
                email: $email
                telephoneNumber: $telephoneNumber
                limit: $limit
                ) {
                id
                firstName
                lastName
                middleName
                username
                }
              }
        '''), variable_values=dict(telephoneNumber=telephone_number, limit=limit))['users']

    def create_b2c_connection_request(self, invited_user_id, connection_type='OTHER'):
        '''See https://docs.tnid.com/company/b2c-features/send-person-b2c-connection-request'''
        return self.client.execute(gql(
            '''
            mutation (
                $invitedUserId: ID!
                $connectionType: B2cConnectionType!
              ) {
                createB2cConnectionRequest (
                invitedUserId: $invitedUserId
                connectionType: $connectionType
                ) {
                id
                status
                type
                insertedAt
                respondedAt
                updatedAt
                company {
                    id
                }
                user {
                    id
                }
                invitedUser {
                    id
                }
                }
              }
        '''), variable_values=dict(invitedUserId=invited_user_id, connectionType=connection_type))['createB2cConnectionRequest']

    def create_b2c_invite(self, user, connection_type='OTHER'):
        '''See https://docs.tnid.com/company/b2c-features/invite-people-as-company'''
        return self.client.execute(gql(
            '''
            mutation (
                $user: InviteUserInput!
                $connectionType: B2cConnectionType!
                    ) {
                createB2cInvite (
                user: $user
                connectionType: $connectionType
                ) {
                id
                status
                type
                insertedAt
                respondedAt
                updatedAt
                company {
                    id
                }
                user {
                    id
                }
                invitedUser {
                    id
                    firstName
                    lastName
                }
                }
              }
        '''), variable_values=dict(user=user, connectionType=connection_type))['createB2cInvite']

    def pending_b2c_connection_requests(self, invited_user_id):
        '''See https://docs.tnid.com/company/b2c-features/list-pending-people-connection-requests'''
        return self.client.execute(gql(
            '''
            query (
                $invitedUserId: ID
                $includedType: B2cConnectionType
                $excludedType: B2cConnectionType
                $limit: Int
              ) {
                pendingB2cConnectionRequests (
                invitedUserId: $invitedUserId
                includedType: $includedType
                excludedType: $excludedType
                limit: $limit
                ) {
                id
                status
                type
                insertedAt
                respondedAt
                updatedAt
                company {
                    id
                }
                user {
                    id
                }
                invitedUser {
                    id
                }
                }
              }
        '''), variable_values=dict(invitedUserId=invited_user_id))['pendingB2cConnectionRequests']


    def b2c_connections(self):
        '''See https://docs.tnid.com/company/b2c-features/get-connected-people'''
        return self.client.execute(gql(
            '''
            query (
                $includedType: B2cConnectionType
                $excludedType: B2cConnectionType
                $limit: Int
              ) {
                b2cConnections (
                includedType: $includedType
                excludedType: $excludedType
                limit: $limit
                ) {
                id
                type
                insertedAt
                updatedAt
                startedAt
                company {
                    id
                }
                connectedUser {
                    id
                }
                }
              }
        '''))['b2cConnections']

    def invite(self, telephone_number, email_address=None):
        users = self.users(telephone_number)
        if len(users) > 0:
            user_id = users[0]['id']
            self.create_b2c_connection_request(user_id)
        elif email_address is not None:
            invite = self.create_b2c_invite(dict(emailAddress=email_address, telephoneNumber=telephone_number))
            user_id = invite['invitedUser']['id']
        else:
            # No email address - need to prompt for one
            return None
        while True:
            time.sleep(5)
            if len(self.pending_b2c_connection_requests(user_id)) == 0:
                break
        connected_users = [connection['connectedUser']['id'] for connection in self.b2c_connections()]
        return user_id in connected_users

