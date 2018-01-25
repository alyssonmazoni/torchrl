import torch
import torch.nn.functional as F

from torchrl.distributions_temp.kl import kl_divergence

from torchrl.models import PGModel


class SurrogatePGModel(PGModel):
    def train(self, batch, num_epochs=1, logger=None):
        # .detach() is used so no gradients are computed w.r.t. to old dists
        for dist in self.saved_dists:
            dist.detach()

        batch['actions'] = self._to_variable(batch['actions'])
        batch['advantages'] = self._to_variable(batch['advantages'])
        batch['old_log_probs'] = torch.cat([
            dist.log_prob(action)
            for dist, action in zip(self.saved_dists, batch['actions'])
        ])

        super().train(batch=batch, num_epochs=num_epochs, logger=logger)

        self.saved_dists = []

    def create_new_dists(self, states):
        # new_probs = F.softmax(self.policy_nn.head(self.policy_nn.body(states)), dim=-1)
        # new_dists = [self.dist(p) for p in new_probs]
        new_parameters = self.forward(states)
        new_dists = self.create_dists(new_parameters)
        # new_dists = [self.create_dist(new_parameter) for new_parameter in new_parameters]

        return new_dists

    def calculate_prob_ratio(self, batch, new_dists):
        new_log_probs = torch.cat([
            new_dist.log_prob(action)
            for new_dist, action in zip(new_dists, batch['actions'])
        ])

        prob_ratio = (new_log_probs - batch['old_log_probs']).exp()

        return prob_ratio

    def add_surrogate_pg_loss(self, batch, new_dists):
        prob_ratio = self.calculate_prob_ratio(batch, new_dists)
        surrogate = prob_ratio * batch['advantages']

        loss = -surrogate.sum()
        self.losses.append(loss)

    def add_losses(self, batch):
        new_dists = self.create_new_dists(batch['state_ts'])

        self.add_surrogate_pg_loss(batch, new_dists)
        self.add_value_nn_loss(batch)

    def entropy(self, dists):
        return torch.cat([dist.entropy() for dist in dists]).mean()

    def kl_divergence(self, new_dists):
        kl_divs = [
            kl_divergence(old_dist, new_dist)
            for old_dist, new_dist in zip(self.saved_dists, new_dists)
        ]

        return torch.cat(kl_divs).mean()

    def write_logs(self, batch, logger):
        new_dists = self.create_new_dists(batch['state_ts'])

        logger.add_log('Policy/Entropy', self.entropy(new_dists).data[0])
        logger.add_log(
            'Policy/KL_div', self.kl_divergence(new_dists).data[0], precision=5)
