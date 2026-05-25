package com.voicebutton

import android.os.Parcel
import android.os.Parcelable

data class ButtonConfig(
    val id: Long = System.currentTimeMillis(),
    val label: String = "",
    val actionType: String = "text",  // "text", "key", "voice"
    val action: String = "",
    val language: String = "es"  // language for voice recognition (default español)
) : Parcelable {
    constructor(parcel: Parcel) : this(
        parcel.readLong(),
        parcel.readString() ?: "",
        parcel.readString() ?: "text",
        parcel.readString() ?: "",
        parcel.readString() ?: "es"
    )

    override fun writeToParcel(parcel: Parcel, flags: Int) {
        parcel.writeLong(id)
        parcel.writeString(label)
        parcel.writeString(actionType)
        parcel.writeString(action)
        parcel.writeString(language)
    }

    override fun describeContents(): Int = 0

    companion object CREATOR : Parcelable.Creator<ButtonConfig> {
        override fun createFromParcel(parcel: Parcel): ButtonConfig = ButtonConfig(parcel)
        override fun newArray(size: Int): Array<ButtonConfig?> = arrayOfNulls(size)
    }
}
