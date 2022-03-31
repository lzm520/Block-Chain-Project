import hashlib
import json
from time import time
from urllib.parse import urlparse
from uuid import uuid4

import requests
from flask import Flask, jsonify, request


class Blockchain:
    def __init__(self):
        self.current_transactions = []
        self.chain = []
        self.nodes = set()
        self.block_generation_interval = 10
        self.difficulty_adjustment_interval = 10
        
        
        # Create the genesis block
        self.new_genesis_block()

    def register_node(self, address):
        """
        Add a new node to the list of nodes

        :param address: Address of node. Eg. 'http://192.168.0.5:5000'
        """

        parsed_url = urlparse(address)
        if parsed_url.netloc:
            self.nodes.add(parsed_url.netloc)
        elif parsed_url.path:
            # Accepts an URL without scheme like '192.168.0.5:5000'.
            self.nodes.add(parsed_url.path)
        else:
            raise ValueError('Invalid URL')


    def valid_chain(self, chain):
        last_block = chain[0]
        current_index = 1

        while current_index < len(chain):
            block = chain[current_index]
            print(f'{last_block}')
            print(f'{block}')
            print("\n-----------\n")
            # Check that the hash of the block is correct
            last_block_hash = last_block['hash']
            if block['previous_hash'] != last_block_hash:
                return False

            # Check that the Proof of Work is correct
            if not self.valid_proof(block, block['difficulty']):
                return False

            last_block = block
            current_index += 1

        return True

    def resolve_conflicts(self):
        """
        This is our consensus algorithm, it resolves conflicts
        by replacing our chain with the longest one in the network.

        :return: True if our chain was replaced, False if not
        """

        neighbours = self.nodes
        new_chain = None

        # We're only looking for chains longer than ours
        max_length = len(self.chain)

        # Grab and verify the chains from all the nodes in our network
        for node in neighbours:
            response = requests.get(f'http://{node}/chain')

            if response.status_code == 200:
                length = response.json()['length']
                chain = response.json()['chain']

                # Check if the length is longer and the chain is valid
                if length > max_length and self.valid_chain(chain):
                    max_length = length
                    new_chain = chain

        # Replace our chain if we discovered a new, valid chain longer than ours
        if new_chain:
            self.chain = new_chain
            return True

        return False
    
    def new_genesis_block(self):
        block = {
            'index': 1,
            'hash': "1",
            'previous_hash': "0",
            'timestamp': time(),
            'transactions': [],
            'difficulty': 4,
            'nonce': 0,
        }
        return block
             
    def new_block(self):
        last_block = self.chain[-1]
        
        block = {
            'index': last_block['index'] + 1,
            'previous_hash': last_block['hash'],
            'timestamp': time(),
            'transactions': self.current_transactions,
        }
        
        block['hash'] = self.hash(block)
        block['difficulty'] = self.get_difficulty()
        block['nonce'] = 0
        block['nonce'] = self.proof_of_work(block)
        
        # Reset the current list of transactions
        self.current_transactions = []

        self.chain.append(block)
        return block
    
    
    def get_difficulty(self):
        last_block = self.last_block()
        if (last_block.index % self.block_generation_interval == 0):
            prev_adjustment_block = self.chain[len(self.chain) - self.difficulty_adjustment_interval]
            time_expected = self.block_generation_interval * self.difficulty_adjustment_interval
            time_taken = last_block.timestamp - prev_adjustment_block.timestamp
            
            if (time_taken < time_expected / 2):
                return prev_adjustment_block.difficulty + 1
            else:
                if (time_expected > time_expected * 2):
                    return prev_adjustment_block.difficulty - 1
                else: 
                    return prev_adjustment_block.difficulty
        else:
            return last_block.difficuly
    
    
    def proof_of_work(self, block):
        nonce = 0
        difficulty = block['difficulty']
        header_hash = self.hash(block)
        while self.valid_proof(header_hash, difficulty) is False:
            nonce += 1
            block['nonce'] = nonce
            header_hash = self.hash(block)

        return nonce

    @staticmethod
    def valid_proof(header_hash, difficulty):
        prefix_target = "0000000000"[0:difficulty]
        guess = f'{header_hash}'.encode()
        guess_hash = hashlib.sha256(guess).hexdigest()
        return guess_hash[:difficulty] == prefix_target
            

    def new_transaction(self, sender, recipient, amount):
        """
        Creates a new transaction to go into the next mined Block

        :param sender: Address of the Sender
        :param recipient: Address of the Recipient
        :param amount: Amount
        :return: The index of the Block that will hold this transaction
        """
        self.current_transactions.append({
            'sender': sender,
            'recipient': recipient,
            'amount': amount,
        })

        return self.last_block['index'] + 1

    @property
    def last_block(self):
        return self.chain[-1]

    @staticmethod
    def hash(block):
        # We must make sure that the Dictionary is Ordered, or we'll have inconsistent hashes
        block_string = json.dumps(block, sort_keys=True).encode()
        return hashlib.sha256(block_string).hexdigest()



# Instantiate the Node
app = Flask(__name__)

# Generate a globally unique address for this node
node_identifier = str(uuid4()).replace('-', '')

# Instantiate the Blockchain
blockchain = Blockchain()


@app.route('/mine', methods=['GET'])
def mine():
    

    block = blockchain.new_block()
    
    blockchain.new_transaction(
        sender="0",
        recipient=node_identifier,
        amount=1,
    )

    response = {
        'message': "New Block Forged",
        'index': block['index'],
        'transactions': block['transactions'],
        'nonce': block['nonce'],
        'previous_hash': block['previous_hash'],
    }
    return jsonify(response), 200


@app.route('/transactions/new', methods=['POST'])
def new_transaction():
    values = request.get_json()

    # Check that the required fields are in the POST'ed data
    required = ['sender', 'recipient', 'amount']
    if not all(k in values for k in required):
        return 'Missing values', 400

    # Create a new Transaction
    index = blockchain.new_transaction(values['sender'], values['recipient'], values['amount'])

    response = {'message': f'Transaction will be added to Block {index}'}
    return jsonify(response), 201




@app.route('/chain', methods=['GET'])
def full_chain():
    response = {
        'chain': blockchain.chain,
        'length': len(blockchain.chain),
    }
    return jsonify(response), 200


@app.route('/nodes/register', methods=['POST'])
def register_nodes():
    values = request.get_json()

    nodes = values.get('nodes')
    if nodes is None:
        return "Error: Please supply a valid list of nodes", 400

    for node in nodes:
        blockchain.register_node(node)

    response = {
        'message': 'New nodes have been added',
        'total_nodes': list(blockchain.nodes),
    }
    return jsonify(response), 201


@app.route('/nodes/resolve', methods=['GET'])
def consensus():
    replaced = blockchain.resolve_conflicts()

    if replaced:
        response = {
            'message': 'Our chain was replaced',
            'new_chain': blockchain.chain
        }
    else:
        response = {
            'message': 'Our chain is authoritative',
            'chain': blockchain.chain
        }

    return jsonify(response), 200


if __name__ == '__main__':
    from argparse import ArgumentParser

    parser = ArgumentParser()
    parser.add_argument('-p', '--port', default=5000, type=int, help='port to listen on')
    args = parser.parse_args()
    port = args.port

    app.run(host='0.0.0.0', port=port)
