import pytest
import ape
from ape import chain, Contract
from ape.types import ContractLog
import time
import os
from web3 import Web3, HTTPProvider
from hexbytes import HexBytes
import json
from ape.utils import ZERO_ADDRESS
from utils.constants import (
    YEARN_FEE_RECEIVER, 
    MAX_INT, 
    ApprovalStatus, 
    ZERO_ADDRESS
)

# we default to local node
w3 = Web3(HTTPProvider(os.getenv("CHAIN_PROVIDER", "http://127.0.0.1:8545")))

# Accounts
@pytest.fixture(scope="session")
def gov(accounts):
    gov = accounts['0x4444AAAACDBa5580282365e25b16309Bd770ce4a']
    gov.balance += 10 ** 18
    # accounts[0].transfer(gov, 10**18)
    yield gov
    
@pytest.fixture(scope="session")
def user(accounts):
    accounts[1].balance += int(100e18)
    assert accounts[1].balance > 0
    yield accounts[1]

@pytest.fixture(scope="session")
def user2(accounts):
    accounts[2].balance += int(100e18)
    assert accounts[2].balance > 0
    yield accounts[2]

@pytest.fixture(scope="session")
def user3(accounts):
    accounts[3].balance += int(100e18)
    assert accounts[3].balance > 0
    yield accounts[3]

@pytest.fixture(scope="session")
def rando(accounts):
    accounts[9].balance += int(100e18)
    assert accounts[9].balance > 0
    yield accounts[9]

@pytest.fixture(scope="session")
def yprisma():
    yield Contract('0xe3668873D944E4A949DA05fc8bDE419eFF543882')

@pytest.fixture(scope="session")
def prisma():
    yield Contract('0xdA47862a83dac0c112BA89c6abC2159b95afd71C')

@pytest.fixture(scope="session")
def yprisma_whale(accounts, fee_receiver, user, yprisma, user2, user3, rando):
    whale = accounts['0x69833361991ed76f9e8DBBcdf9ea1520fEbFb4a7']
    whale.balance += 10 ** 18
    yprisma.transfer(user, 100_000 * 10 ** 18, sender=whale)
    yprisma.transfer(user2, 100_000 * 10 ** 18, sender=whale)
    yprisma.transfer(user3, 100_000 * 10 ** 18, sender=whale)
    yprisma.transfer(fee_receiver, 200_000 * 10 ** 18, sender=whale)
    yprisma.transfer(rando, 100_000 * 10 ** 18, sender=whale)
    yield whale


@pytest.fixture(scope="session")
def mkusd():
    yield Contract('0x4591DBfF62656E7859Afe5e45f6f47D3669fBB28')

@pytest.fixture(scope="session")
def yvmkusd():
    yield Contract('0x04AeBe2e4301CdF5E9c57B01eBdfe4Ac4B48DD13')

@pytest.fixture(scope="session")
def dai_whale(accounts):
    whale = accounts['0x40ec5B33f54e0E8A33A975908C5BA1c14e5BbbDf']
    whale.balance += 10 ** 18
    yield whale

@pytest.fixture(scope="session")
def dai():
    yield Contract('0x6B175474E89094C44Da98b954EedeAC495271d0F')

@pytest.fixture(scope="session")
def yvmkusd_whale(accounts, yvmkusd, fee_receiver, mkusd):
    whale = accounts['0x93A62dA5a14C80f265DAbC077fCEE437B1a0Efde']
    sp = accounts['0xed8B26D99834540C5013701bB3715faFD39993Ba']
    sp.balance += 10 ** 18
    mkusd.approve(yvmkusd, 2**256-1, sender=sp)
    yvmkusd.deposit(mkusd.balanceOf(sp), whale, sender=sp)
    whale.balance += 10 ** 18
    yvmkusd.transfer(fee_receiver, 100_000 * 10 ** 18, sender=whale)
    yield whale

@pytest.fixture(scope="session")
def staker(project, yprisma, user, gov, prisma_vault):
    start_time = Contract('0x5d17eA085F2FF5da3e6979D5d26F1dBaB664ccf8').startTime()
    start_time = 0
    staker = user.deploy(
        project.YearnBoostedStaker, 
        yprisma, 
        4, # <-- Number of growth weeks
        start_time,
        gov
    )
    yield staker

@pytest.fixture(scope="session")
def prisma_vault():
    yield Contract('0x06bDF212C290473dCACea9793890C5024c7Eb02c')

@pytest.fixture(scope="session")
def gov_token(yprisma):
    yield yprisma

@pytest.fixture(scope="session")
def stable_token(yvmkusd):
    yield yvmkusd

@pytest.fixture(scope="session")
def rewards(project, user, staker, gov_token, stable_token, gov):
    rewards_contract = user.deploy(
        project.SingleTokenRewardDistributor,
        staker,
        stable_token,
        gov
    )
    yield rewards_contract

@pytest.fixture(scope="session")
def fee_receiver(rewards, accounts, gov_token, stable_token):
    fee_receiver = YEARN_FEE_RECEIVER
    fr_account = accounts[fee_receiver]
    fr_account.balance += 20 ** 18
    gov_token.approve(rewards, 2**256-1, sender=fr_account)
    stable_token.approve(rewards, 2**256-1, sender=fr_account)
    yield Contract(fee_receiver)

@pytest.fixture(scope="session")
def fee_receiver_acc(rewards, accounts, gov_token, stable_token):
    fee_receiver = YEARN_FEE_RECEIVER
    fr_account = accounts[fee_receiver]
    fr_account.balance += 20 ** 18
    gov_token.approve(rewards, 2**256-1, sender=fr_account)
    stable_token.approve(rewards, 2**256-1, sender=fr_account)
    yield fr_account

@pytest.fixture(scope="function")
def setup_rewards(user, accounts, staker, gov, user2, yprisma, yvmkusd, rewards, fee_receiver):
    fr_account = accounts[fee_receiver.address]
    fr_account.balance += 20 ** 18
    yprisma.approve(staker, 2**256-1, sender=user)
    yprisma.approve(staker, 2**256-1, sender=user2)
    yprisma.approve(rewards, 2**256-1, sender=fr_account)
    yvmkusd.approve(rewards, 2**256-1, sender=fr_account)

    # Deposit to staker
    amt = 10_000 * 10 ** 18
    staker.deposit(amt, sender=user)
    staker.deposit(amt, sender=user2)

    # Enable deposits
    owner = accounts[staker.owner()]
    owner.balance += 10**18
    staker.setWeightedDepositor(rewards, True, sender=owner)
    rewards.configureRecipient(ZERO_ADDRESS, sender=user)

    # Deposit to rewards
    amt = 10_000 * 10 ** 18
    rewards.depositReward(amt, sender=fr_account)
    week = rewards.getWeek()
    assert amt == rewards.weeklyRewardAmount(week)