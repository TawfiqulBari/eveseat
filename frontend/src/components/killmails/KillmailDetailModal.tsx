import React from 'react'
import { Modal } from '../common/Modal'
import { KillmailDetail } from '../../services/killmails'
import { formatISK, formatSecurityStatus } from '../../utils/formatters'
import { formatDistanceToNow } from 'date-fns'

interface KillmailDetailModalProps {
  killmail: KillmailDetail | null
  isOpen: boolean
  onClose: () => void
}

export const KillmailDetailModal: React.FC<KillmailDetailModalProps> = ({
  killmail,
  isOpen,
  onClose,
}) => {
  if (!killmail) return null

  const killmailData = killmail.killmail_data || {}
  const victim = killmailData.victim || {}
  const attackers = killmailData.attackers || []

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title={`Killmail ${killmail.killmail_id}`}
      size="xl"
      footer={
        <button
          onClick={onClose}
          className="px-4 py-2 bg-eve-gray hover:bg-eve-gray-dark text-white rounded-lg transition-colors"
        >
          Close
        </button>
      }
    >
      <div className="space-y-6">
        {/* Victim Info */}
        <div className="bg-eve-darker rounded-lg p-4">
          <h3 className="text-lg font-semibold text-white mb-4">Victim</h3>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <span className="text-gray-400">Character:</span>
              <span className="ml-2 text-white">{killmail.victim_character_name || 'Unknown'}</span>
            </div>
            <div>
              <span className="text-gray-400">Corporation:</span>
              <span className="ml-2 text-white">{killmail.victim_corporation_name || 'Unknown'}</span>
            </div>
            <div>
              <span className="text-gray-400">Ship:</span>
              <span className="ml-2 text-white">{killmail.victim_ship_type_name || 'Unknown'}</span>
            </div>
            <div>
              <span className="text-gray-400">System:</span>
              <span className="ml-2 text-eve-blue">{killmail.system_name || 'Unknown'}</span>
            </div>
            <div>
              <span className="text-gray-400">Value:</span>
              <span className="ml-2 text-yellow-400 font-medium">
                {killmail.value ? formatISK(killmail.value) : 'N/A'}
              </span>
            </div>
            <div>
              <span className="text-gray-400">Time:</span>
              <span className="ml-2 text-white">
                {formatDistanceToNow(new Date(killmail.time), { addSuffix: true })}
              </span>
            </div>
          </div>
        </div>

        {/* Attackers */}
        {attackers.length > 0 && (
          <div className="bg-eve-darker rounded-lg p-4">
            <h3 className="text-lg font-semibold text-white mb-4">
              Attackers ({attackers.length})
            </h3>
            <div className="space-y-2 max-h-64 overflow-y-auto">
              {attackers.map((attacker: any, idx: number) => (
                <div
                  key={idx}
                  className="flex items-center justify-between p-2 bg-eve-dark rounded hover:bg-eve-gray transition-colors"
                >
                  <div>
                    <div className="text-white font-medium">
                      {attacker.character_name || `Character ${attacker.character_id || 'Unknown'}`}
                    </div>
                    <div className="text-sm text-gray-400">
                      {attacker.ship_type_name || `Ship Type ${attacker.ship_type_id || 'Unknown'}`}
                      {attacker.damage_done && ` • ${attacker.damage_done.toLocaleString()} damage`}
                    </div>
                  </div>
                  {attacker.final_blow && (
                    <span className="px-2 py-1 bg-red-900/30 text-red-400 text-xs rounded">
                      Final Blow
                    </span>
                  )}
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Items */}
        {victim.items && victim.items.length > 0 && (
          <div className="bg-eve-darker rounded-lg p-4">
            <h3 className="text-lg font-semibold text-white mb-4">
              Items ({victim.items.length})
            </h3>
            <div className="grid grid-cols-2 md:grid-cols-3 gap-2 max-h-64 overflow-y-auto">
              {victim.items.map((item: any, idx: number) => (
                <div
                  key={idx}
                  className="p-2 bg-eve-dark rounded text-sm"
                >
                  <div className="text-white">{item.type_name || `Type ${item.type_id}`}</div>
                  {item.quantity > 1 && (
                    <div className="text-gray-400">Qty: {item.quantity}</div>
                  )}
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Actions */}
        <div className="flex gap-2">
          {killmail.zkill_url && (
            <a
              href={killmail.zkill_url}
              target="_blank"
              rel="noopener noreferrer"
              className="px-4 py-2 bg-eve-blue hover:bg-eve-blue-dark text-white rounded-lg transition-colors"
            >
              View on zKillboard
            </a>
          )}
        </div>
      </div>
    </Modal>
  )
}

