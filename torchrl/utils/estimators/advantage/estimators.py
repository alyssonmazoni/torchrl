from torchrl.utils.estimators.estimation_funcs import gae_estimation


class CompleteReturn:
    def __call__(self, batch):
        return batch.return_


class Baseline:
    def __call__(self, batch):
        return batch.return_ - batch.state_value


class GAE:
    def __init__(self, gamma=0.99, gae_lambda=0.95):
        self.gamma = gamma
        self.gae_lambda = gae_lambda

    def __call__(self, batch):
        return gae_estimation(
            rewards=batch.reward,
            dones=batch.done,
            state_values=batch.state_value,
            gamma=self.gamma,
            gae_lambda=self.gae_lambda)