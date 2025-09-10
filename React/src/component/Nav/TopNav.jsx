import React from 'react'
import './TopNav.css'
import maleAvatar from '../../assets/images/male.jpg'
// import femaleAvatar from '../../assets/images/female.jpg'

const TopNav = () => {
  return (
    <div className='top-nav-container'>
        <button className='top-nav-darkmode'>
            <i className="fa-regular fa-moon fa-flip-horizontal"></i>
        </button>

        <button className='top-nav-bell'>
            <i className="fa-regular fa-bell"></i>
        </button>

        <button className="top-nav-user">
            <img src={maleAvatar} alt="avatar" />
            <ul>
                <li>Welcome back,</li>
                <li>JEON</li>
            </ul>
            <i className="fa-solid fa-chevron-down"></i>
        </button>
    </div>
  )
}

export default TopNav
