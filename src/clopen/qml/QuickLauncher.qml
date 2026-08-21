import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtQuick.Window

Window {
    id: root
    width: 340
    height: Math.min(452, 106 + Math.max(1, clopen.groupItems.length) * 46)
    visible: false
    color: "transparent"
    title: "Clopen 快速操作"
    flags: Qt.Tool | Qt.FramelessWindowHint | Qt.NoDropShadowWindowHint | Qt.WindowStaysOnTopHint

    readonly property bool darkMode: clopen.darkMode
    readonly property color textPrimary: darkMode ? "#F6F7FA" : "#20242A"
    readonly property color textSecondary: darkMode ? "#B8C0CB" : "#67717E"
    property bool closeArmed: false

    onVisibleChanged: {
        closeArmed = false
        if (visible) closeArmTimer.restart()
    }
    onActiveChanged: {
        if (visible && closeArmed && !active) visible = false
    }
    Timer {
        id: closeArmTimer
        interval: 220
        repeat: false
        onTriggered: root.closeArmed = true
    }

    GlassPane {
        anchors.fill: parent
        darkMode: root.darkMode
        cornerRadius: 20
        density: root.darkMode ? 0.034 : 0.090
        highlight: 0.10
    }

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 12
        spacing: 8

        Text {
            text: "快速操作"
            color: root.textPrimary
            font.pixelSize: 12
            font.weight: Font.DemiBold
            renderType: Text.NativeRendering
            Layout.leftMargin: 2
        }

        TextField {
            id: search
            Layout.fillWidth: true
            Layout.preferredHeight: 38
            placeholderText: "搜索组合或软件…"
            color: root.textPrimary
            placeholderTextColor: root.textSecondary
            leftPadding: 13
            rightPadding: 13
            topPadding: 0
            bottomPadding: 0
            verticalAlignment: TextInput.AlignVCenter
            font.pixelSize: 13
            renderType: Text.NativeRendering
            selectByMouse: true
            background: GlassPane {
                darkMode: root.darkMode
                cornerRadius: 11
                density: root.darkMode ? 0.040 : 0.100
                highlight: search.activeFocus ? 0.28 : 0.12
            }
            Component.onCompleted: forceActiveFocus()
        }

        ListView {
            id: list
            Layout.fillWidth: true
            Layout.fillHeight: true
            spacing: 5
            clip: true
            model: clopen.groupItems
            delegate: Item {
                required property var modelData
                width: list.width
                height: visible ? 40 : 0
                visible: search.text.length === 0 || modelData.name.toLowerCase().indexOf(search.text.toLowerCase()) >= 0

                GlassButton {
                    anchors.fill: parent
                    text: (modelData.active ? "关闭  " : "开启  ") + modelData.name
                    darkMode: root.darkMode
                    quiet: true
                    onClicked: {
                        root.visible = false
                        clopen.toggleGroupByName(modelData.name)
                    }
                }
                Rectangle {
                    visible: modelData.active
                    width: 6; height: 6; radius: 3
                    anchors.right: parent.right
                    anchors.rightMargin: 12
                    anchors.verticalCenter: parent.verticalCenter
                    color: "#43D68B"
                }
            }
        }

        RowLayout {
            Layout.fillWidth: true
            spacing: 6
            GlassButton {
                Layout.fillWidth: true
                text: "打开主界面"
                darkMode: root.darkMode
                onClicked: { root.visible = false; clopen.showMain() }
            }
            GlassButton {
                Layout.fillWidth: true
                text: "退出 Clopen"
                darkMode: root.darkMode
                onClicked: { root.visible = false; clopen.quitApplication() }
            }
        }
    }

    Shortcut { sequence: "Escape"; onActivated: root.visible = false }
}
