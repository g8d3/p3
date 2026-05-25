package com.voicebutton

import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import android.widget.ImageButton
import android.widget.TextView
import androidx.recyclerview.widget.RecyclerView

class ButtonAdapter(
    private var items: MutableList<ButtonConfig>,
    private val onEdit: (ButtonConfig) -> Unit,
    private val onDelete: (ButtonConfig) -> Unit,
    private val onMoveUp: (Int) -> Unit,
    private val onMoveDown: (Int) -> Unit
) : RecyclerView.Adapter<ButtonAdapter.ViewHolder>() {

    class ViewHolder(v: View) : RecyclerView.ViewHolder(v) {
        val tvLabel: TextView = v.findViewById(R.id.tvLabel)
        val tvAction: TextView = v.findViewById(R.id.tvAction)
        val btnEdit: ImageButton = v.findViewById(R.id.btnEdit)
        val btnDelete: ImageButton = v.findViewById(R.id.btnDelete)
        val btnUp: ImageButton = v.findViewById(R.id.btnUp)
        val btnDown: ImageButton = v.findViewById(R.id.btnDown)
    }

    override fun onCreateViewHolder(parent: ViewGroup, viewType: Int): ViewHolder {
        val v = LayoutInflater.from(parent.context)
            .inflate(R.layout.item_button, parent, false)
        val h = ViewHolder(v)
        h.btnEdit.setOnClickListener { onEdit(items[h.adapterPosition]) }
        h.btnDelete.setOnClickListener { onDelete(items[h.adapterPosition]) }
        h.btnUp.setOnClickListener { onMoveUp(h.adapterPosition) }
        h.btnDown.setOnClickListener { onMoveDown(h.adapterPosition) }
        return h
    }

    override fun onBindViewHolder(holder: ViewHolder, position: Int) {
        val item = items[position]
        holder.tvLabel.text = item.label
        holder.tvAction.text = when (item.actionType) {
            "text" -> "\uD83D\uDCDD ${item.action}"
            "key" -> "\uD83D\uDD11 ${item.action}"
            "voice" -> "\uD83C\uDFA4 Dictado"
            else -> item.action
        }
    }

    override fun getItemCount(): Int = items.size

    fun update(newItems: List<ButtonConfig>) {
        items.clear()
        items.addAll(newItems)
        notifyDataSetChanged()
    }
}
